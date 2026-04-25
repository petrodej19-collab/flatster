# Phase 3: React Frontend — Design Spec

**Project:** NepremicnineTracker
**Date:** 2026-04-07
**Scope:** React SPA with auth, project management, listings browsing, favorites/comparison, price history charts

---

## 1. Overview

Phase 3 adds a React frontend that consumes the Phase 2 backend API. Users can register/login, create projects with scraping filters, browse paginated/filtered/sorted listings, favorite listings, compare favorites side-by-side, and view price history charts. Includes a small backend addition for persisted favorites.

### Phases roadmap

- **Phase 1 (done):** Foundation + Scraper
- **Phase 2 (done):** Backend API
- **Phase 3 (this spec):** React frontend
- **Phase 4:** AI scoring + polish

---

## 2. Tech Stack

- **React 18** with TypeScript
- **Vite** — build tool and dev server
- **React Router** — client-side routing
- **TanStack Query** — server state management (caching, refetching, loading states)
- **React Context** — auth state only (token + current user)
- **shadcn/ui** — component library (Tailwind + Radix primitives)
- **Tailwind CSS** — styling
- **Recharts** — price history line charts
- **Axios** — HTTP client with auth interceptor
- **Vitest + @testing-library/react + msw** — testing

---

## 3. Project Structure

```
frontend/
    public/
    src/
        api/
            client.ts              # Axios instance with auth interceptor
            auth.ts                # useLogin, useRegister, useCurrentUser
            projects.ts            # useProjects, useProject, useCreateProject, etc.
            listings.ts            # useListings, useListing
            favorites.ts           # useFavorites, useToggleFavorite
        components/
            Layout.tsx             # Shell: header + main content area
            ProtectedRoute.tsx     # Redirect to login if not authenticated
            LoadingSpinner.tsx
            ui/                    # shadcn/ui generated components
        features/
            auth/
                LoginPage.tsx          # Login/Register with tab toggle
                AuthContext.tsx         # Token storage, current user, login/logout
            projects/
                ProjectsPage.tsx       # Dashboard grid of project cards
                ProjectDetailPage.tsx  # Listings table + project settings panel
                ProjectCreateDialog.tsx # Modal form for creating a project
                ProjectSettingsPanel.tsx # Edit filters, toggle active, trigger scrape
            listings/
                ListingsTable.tsx      # Filterable, sortable, paginated table
                ListingDetailPage.tsx  # Full detail with images, scores, price chart
                PriceHistoryChart.tsx  # Recharts line chart
                ComparisonPage.tsx     # Side-by-side comparison of favorited listings
                FavoriteButton.tsx     # Star toggle
        lib/
            utils.ts               # Formatters (price, date, score badge)
            constants.ts           # REGIONS, SUBREGIONS, PROPERTY_TYPES, ROOM_TYPES
        App.tsx                    # Router setup
        main.tsx                   # Entry point
    package.json
    tsconfig.json
    vite.config.ts
    tailwind.config.ts
    components.json                # shadcn/ui config
```

---

## 4. Backend Additions

### 4.1 Favorites Model

New table `favorites`:

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK -> Users, indexed |
| listing_id | UUID | FK -> Listings, indexed |
| created_at | TIMESTAMP | server_default=now() |

Unique constraint on `(user_id, listing_id)`.

### 4.2 Favorites Endpoints

**`POST /api/favorites/{listing_id}`** — add favorite. Returns 201. Returns 409 if already favorited.

**`DELETE /api/favorites/{listing_id}`** — remove favorite. Returns 204. Returns 404 if not favorited.

**`GET /api/favorites`** — list all favorited listings for the current user. Returns `list[ListingSummary]` (reuses existing schema). Includes listings across all projects.

### 4.3 Listing Count on Projects

Add `listing_count: int` to `ProjectResponse` — computed via a subquery count of listings per project in the list/get endpoints.

### 4.4 CORS

Add `CORSMiddleware` to FastAPI `main.py`. New config setting:

```python
CORS_ORIGINS: list[str] = ["http://localhost:5173"]
```

### 4.5 Files Changed/Created (backend)

- Create: `backend/app/models/favorite.py`
- Create: `backend/app/api/favorites.py`
- Create: `backend/alembic/versions/xxxx_add_favorites.py`
- Modify: `backend/app/models/__init__.py` (add Favorite import)
- Modify: `backend/app/main.py` (include favorites router, add CORS middleware)
- Modify: `backend/app/api/projects.py` (add listing_count to queries)
- Modify: `backend/app/schemas/project.py` (add listing_count field)
- Modify: `backend/app/config.py` (add CORS_ORIGINS)

---

## 5. Authentication Flow

### 5.1 Auth Context (`AuthContext.tsx`)

Stores JWT token in `localStorage`. Provides:
- `token` — current JWT string or null
- `user` — current user object (from `/api/auth/me`) or null
- `login(email, password)` — calls API, stores token, fetches user
- `register(email, password)` — calls API, stores token, fetches user
- `logout()` — clears token, clears TanStack Query cache, redirects to login
- `isLoading` — true while checking token validity on app start

### 5.2 API Client (`client.ts`)

Axios instance with:
- `baseURL` from `VITE_API_URL` env var (defaults to `http://localhost:8000`)
- Request interceptor: attaches `Authorization: Bearer <token>` header if token exists
- Response interceptor: on 401, clears token and redirects to `/login`

### 5.3 Login Page (`/login`)

Single page with two tabs: **Login** and **Register**. Both forms have email + password fields. Register tab enforces 8-character minimum (matching backend). On success, redirects to `/projects`.

### 5.4 Protected Routes

All routes except `/login` wrapped in `ProtectedRoute`. No token → redirect to `/login`. On app load, validates existing token via `GET /api/auth/me`.

---

## 6. Routes

| Route | Page | Auth Required |
|---|---|---|
| `/login` | LoginPage | No |
| `/projects` | ProjectsPage | Yes |
| `/projects/:id` | ProjectDetailPage | Yes |
| `/projects/:id/listings/:listingId` | ListingDetailPage | Yes |
| `/compare` | ComparisonPage | Yes |

Default route (`/`) redirects to `/projects` if authenticated, `/login` if not.

---

## 7. Pages

### 7.1 Projects Page (`/projects`)

Grid of project cards. Each card shows:
- Project name
- Scrape URL (truncated)
- Active/inactive badge
- Last scraped timestamp (relative, e.g., "2 hours ago")
- Listing count

Top-right: "New Project" button → opens `ProjectCreateDialog`.

### 7.2 Project Create Dialog

Modal form with:
- Name (text input, required)
- Transaction type (select: Prodaja / Oddaja)
- Region (select from REGIONS)
- Sub-region (select from SUBREGIONS[region], optional, updates dynamically when region changes)
- Property type (select from PROPERTY_TYPES)
- Rooms (multi-select from ROOM_TYPES, only shown when property_type = "stanovanje")
- Price range (min/max number inputs, optional)
- Size range (min/max number inputs, optional)
- Year range (min/max number inputs, optional)

Region, sub-region, property type, and room options are hardcoded in the frontend constants file, mirroring the backend constants. On submit, calls `POST /api/projects`, redirects to the new project's detail page.

### 7.3 Project Detail Page (`/projects/:id`)

Two-panel layout:

**Left panel (~70%): Listings Table**
- Columns: favorite star, title, price, price/m2, size, rooms, floor, year, score badge, status badge, first seen
- Filters bar above table: status dropdown, price range, size range
- Sortable column headers: price, size, score, price/m2, first seen
- Pagination: page numbers, per_page selector (25/50/100)
- Row click navigates to listing detail
- Star icon toggles favorite

Score badge colors: green (70+), yellow (40-69), red (0-39), gray (null).

**Right panel (~30%): Project Settings**
- Project name (editable inline)
- Filters summary (read-only)
- Active toggle switch
- "Edit Filters" button → opens create dialog pre-filled
- "Scrape Now" button → calls scrape endpoint, shows loading spinner, displays result toast
- Last scraped timestamp
- "Delete Project" button with confirmation dialog

### 7.4 Listing Detail Page (`/projects/:id/listings/:listingId`)

**Header:** title, location, favorite star, back button.

**Key facts + Score (two columns):**
- Left: price (large), price/m2, size, rooms, floor, year built/renovated, energy class, agency, status badge
- Right: basic score as large prominent number with color. AI score placeholder (grayed out, "Phase 4").

**Image gallery:** horizontal scrollable thumbnails, click to expand in lightbox.

**Price history chart:** Recharts line chart, date on x-axis, price on y-axis. Single data point shown as dot with label.

**Description:** full text below chart.

**Metadata footer:** external link to nepremicnine.net, first seen / last seen, consecutive misses count.

### 7.5 Comparison Page (`/compare`)

Accessible from header nav: **Projects** | **Compare (N)**.

Side-by-side cards (2-4 listings). Each card:
- Thumbnail image
- Title, location
- Price, price/m2, size, rooms, floor, year
- Basic score badge, status badge
- Link to full listing detail
- Star toggle to remove from comparison

If more than 4 favorites, user picks which to compare. Empty state: "No favorites yet. Star listings from any project to compare them here."

---

## 8. API Hooks (TanStack Query)

### auth.ts
- `useLogin()` — mutation, calls `POST /api/auth/login`
- `useRegister()` — mutation, calls `POST /api/auth/register`
- `useCurrentUser()` — query, calls `GET /api/auth/me`

### projects.ts
- `useProjects()` — query, calls `GET /api/projects`
- `useProject(id)` — query, calls `GET /api/projects/{id}`
- `useCreateProject()` — mutation, invalidates projects query
- `useUpdateProject()` — mutation, invalidates project + projects queries
- `useDeleteProject()` — mutation, invalidates projects query
- `useTriggerScrape(id)` — mutation, invalidates project + listings queries

### listings.ts
- `useListings(projectId, filters)` — query, calls `GET /api/projects/{id}/listings` with filter/sort/page params
- `useListing(projectId, listingId)` — query, calls `GET /api/projects/{id}/listings/{listingId}`

### favorites.ts
- `useFavorites()` — query, calls `GET /api/favorites`
- `useToggleFavorite()` — mutation, calls POST or DELETE based on current state, invalidates favorites query

---

## 9. Development Setup

### Vite dev server

- `frontend/` directory at project root (sibling to `backend/`)
- Dev server on port 5173
- Proxy `/api` requests to `http://localhost:8000` via `vite.config.ts` `server.proxy`
- Hot module replacement

### Docker integration

New `frontend` service in `docker-compose.yml`:
- `node:20-alpine` image
- Mounts `./frontend` as volume
- Runs `npm run dev -- --host 0.0.0.0`
- Depends on `app` (backend) service
- Exposes port 5173

### Environment

- `VITE_API_URL` — backend URL (defaults to `http://localhost:8000`, overridden by Vite proxy in dev)

---

## 10. Testing Strategy

### Unit tests

- **API hooks**: mock API responses with `msw`, verify TanStack Query hooks return correct data/loading/error states
- **Components**: render with test data, verify elements and interactive behavior (filter changes, star toggles, form validation)

### Key test files

- `src/api/__tests__/auth.test.ts`
- `src/api/__tests__/projects.test.ts`
- `src/features/auth/__tests__/LoginPage.test.tsx`
- `src/features/projects/__tests__/ProjectCreateDialog.test.tsx`
- `src/features/listings/__tests__/ListingsTable.test.tsx`

### Tools

- Vitest (Vite-native)
- `@testing-library/react`
- `msw` (Mock Service Worker)

Focus on behavior, not implementation. No snapshot tests.

---

## 11. Frontend Constants

`lib/constants.ts` mirrors the backend's `scraper/constants.py`:
- `REGIONS` — `Record<string, string>` (slug → display name)
- `SUBREGIONS` — `Record<string, Record<string, string>>` (region slug → sub-region slug → display name)
- `PROPERTY_TYPES` — `Record<string, string>`
- `ROOM_TYPES` — `string[]`
- `TRANSACTION_TYPES` — `string[]`

These are static and hardcoded. They only change if the backend constants change (which requires a code update anyway).

---

## 12. Out of Scope for Phase 3

- Server-side rendering (SSR)
- Production Docker build (nginx static serving)
- Email notifications or alerts
- Export functionality (CSV, PDF)
- Mobile-responsive design (desktop-first, responsive later)
- AI scoring UI (Phase 4)
- Internationalization (Slovenian-only labels are fine)
- Dark mode
