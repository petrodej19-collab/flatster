# Phase 3: React Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a React SPA with auth, project management, listing browsing with filters/sorting, favorites, comparison, and price history charts — consuming the Phase 2 backend API.

**Architecture:** Feature-based modules (auth, projects, listings) with centralized API hooks (TanStack Query), auth via React Context + localStorage JWT, shadcn/ui components on Tailwind. Small backend additions (favorites model/endpoints, listing count, CORS).

**Tech Stack:** React 18, TypeScript, Vite, React Router, TanStack Query, shadcn/ui, Tailwind CSS, Recharts, Axios, Vitest + Testing Library + msw

---

## File Map

### Backend additions

| File | Responsibility |
|---|---|
| `backend/app/models/favorite.py` | Favorite model (user_id + listing_id) |
| `backend/app/api/favorites.py` | POST/DELETE/GET favorites endpoints |
| `backend/alembic/versions/xxxx_add_favorites.py` | Migration for favorites table |

### Backend modifications

| File | Changes |
|---|---|
| `backend/app/models/__init__.py` | Add Favorite import |
| `backend/app/main.py` | Add favorites router, CORS middleware |
| `backend/app/config.py` | Add CORS_ORIGINS setting |
| `backend/app/api/projects.py` | Add listing_count to project queries |
| `backend/app/schemas/project.py` | Add listing_count field |

### Frontend new files

| File | Responsibility |
|---|---|
| `frontend/package.json` | Dependencies and scripts |
| `frontend/tsconfig.json` | TypeScript config |
| `frontend/vite.config.ts` | Vite config with API proxy |
| `frontend/tailwind.config.ts` | Tailwind config |
| `frontend/postcss.config.js` | PostCSS for Tailwind |
| `frontend/index.html` | Entry HTML |
| `frontend/src/main.tsx` | React entry point |
| `frontend/src/App.tsx` | Router setup |
| `frontend/src/index.css` | Tailwind imports + shadcn theme |
| `frontend/src/api/client.ts` | Axios instance with auth interceptor |
| `frontend/src/api/auth.ts` | Auth TanStack Query hooks |
| `frontend/src/api/projects.ts` | Project TanStack Query hooks |
| `frontend/src/api/listings.ts` | Listing TanStack Query hooks |
| `frontend/src/api/favorites.ts` | Favorites TanStack Query hooks |
| `frontend/src/lib/utils.ts` | cn() helper, formatters |
| `frontend/src/lib/constants.ts` | Regions, property types, room types |
| `frontend/src/components/Layout.tsx` | App shell (header + nav + content) |
| `frontend/src/components/ProtectedRoute.tsx` | Auth guard |
| `frontend/src/components/LoadingSpinner.tsx` | Spinner component |
| `frontend/src/features/auth/AuthContext.tsx` | Auth context provider |
| `frontend/src/features/auth/LoginPage.tsx` | Login/Register page |
| `frontend/src/features/projects/ProjectsPage.tsx` | Projects dashboard |
| `frontend/src/features/projects/ProjectDetailPage.tsx` | Project detail with listings |
| `frontend/src/features/projects/ProjectCreateDialog.tsx` | Create/edit project modal |
| `frontend/src/features/projects/ProjectSettingsPanel.tsx` | Project settings sidebar |
| `frontend/src/features/listings/ListingsTable.tsx` | Paginated/filtered/sorted table |
| `frontend/src/features/listings/ListingDetailPage.tsx` | Listing detail view |
| `frontend/src/features/listings/PriceHistoryChart.tsx` | Recharts line chart |
| `frontend/src/features/listings/ComparisonPage.tsx` | Compare favorites side-by-side |
| `frontend/src/features/listings/FavoriteButton.tsx` | Star toggle |

### Docker modification

| File | Changes |
|---|---|
| `docker-compose.yml` | Add frontend service |

---

### Task 1: Backend — Favorites Model and Migration

**Files:**
- Create: `backend/app/models/favorite.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/xxxx_add_favorites.py`

- [ ] **Step 1: Create Favorite model**

Create `backend/app/models/favorite.py`:

```python
import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Favorite(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="uq_favorites_user_listing"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id"), index=True
    )
```

- [ ] **Step 2: Add Favorite to models __init__**

In `backend/app/models/__init__.py`, add:

```python
from app.models.favorite import Favorite
```

And update `__all__` to include `"Favorite"`.

- [ ] **Step 3: Create migration**

Create `backend/alembic/versions/b3a1f2c8e9d4_add_favorites.py`:

```python
"""add favorites table

Revision ID: b3a1f2c8e9d4
Revises: 74bc0191d77a
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b3a1f2c8e9d4"
down_revision = "74bc0191d77a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "favorites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listings.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "listing_id", name="uq_favorites_user_listing"),
    )


def downgrade() -> None:
    op.drop_table("favorites")
```

- [ ] **Step 4: Verify import**

Run: `cd backend && python3 -c "from app.models.favorite import Favorite; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/favorite.py backend/app/models/__init__.py backend/alembic/versions/b3a1f2c8e9d4_add_favorites.py
git commit -m "feat: add Favorite model and migration"
```

---

### Task 2: Backend — Favorites Endpoints

**Files:**
- Create: `backend/app/api/favorites.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create favorites router**

Create `backend/app/api/favorites.py`:

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.favorite import Favorite
from app.models.listing import Listing
from app.models.user import User
from app.schemas.listing import ListingSummary

router = APIRouter()


@router.post("/{listing_id}", status_code=201)
async def add_favorite(
    listing_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Check listing exists
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    # Check not already favorited
    result = await session.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.listing_id == listing_id,
        )
    )
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already favorited")

    fav = Favorite(user_id=current_user.id, listing_id=listing_id)
    session.add(fav)
    await session.commit()
    return {"status": "favorited"}


@router.delete("/{listing_id}", status_code=204)
async def remove_favorite(
    listing_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.listing_id == listing_id,
        )
    )
    fav = result.scalar_one_or_none()
    if fav is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not favorited")

    await session.delete(fav)
    await session.commit()


@router.get("", response_model=list[ListingSummary])
async def list_favorites(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Listing)
        .join(Favorite, Favorite.listing_id == Listing.id)
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
    )
    listings = result.scalars().all()
    return [ListingSummary.model_validate(l) for l in listings]
```

- [ ] **Step 2: Add favorites router and CORS to main.py**

Add to the imports in `backend/app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

from app.api.favorites import router as favorites_router
from app.config import settings
```

After the `app = FastAPI(...)` line, add:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Add the router include:

```python
app.include_router(favorites_router, prefix="/api/favorites", tags=["favorites"])
```

- [ ] **Step 3: Add CORS_ORIGINS to config**

In `backend/app/config.py`, add after `SOLD_DETECTION_MISSES`:

```python
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
```

- [ ] **Step 4: Verify import**

Run: `cd backend && python3 -c "from app.api.favorites import router; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Run all tests**

Run: `cd backend && python3 -m pytest -v`
Expected: All 77 tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/favorites.py backend/app/main.py backend/app/config.py
git commit -m "feat: add favorites endpoints and CORS middleware"
```

---

### Task 3: Backend — Listing Count on Projects

**Files:**
- Modify: `backend/app/schemas/project.py`
- Modify: `backend/app/api/projects.py`

- [ ] **Step 1: Add listing_count to ProjectResponse**

In `backend/app/schemas/project.py`, add the field to `ProjectResponse`:

```python
class ProjectResponse(BaseModel):
    id: UUID
    name: str
    filters: dict
    scrape_url: str
    is_active: bool
    ai_scoring_enabled: bool
    last_scraped_at: datetime | None
    created_at: datetime
    listing_count: int = 0

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Add listing count to project queries**

In `backend/app/api/projects.py`, add to imports:

```python
from sqlalchemy import func, select
```

(Replace the existing `from sqlalchemy import select` import.)

Also add the Listing import:

```python
from app.models.listing import Listing
```

Modify the `list_projects` endpoint to include listing count. Replace the entire function:

```python
@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(Project).where(Project.user_id == current_user.id)
    )
    projects = result.scalars().all()

    # Get listing counts in one query
    count_result = await session.execute(
        select(Listing.project_id, func.count(Listing.id))
        .where(Listing.project_id.in_([p.id for p in projects]))
        .group_by(Listing.project_id)
    )
    counts = dict(count_result.all())

    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            filters=p.filters,
            scrape_url=p.scrape_url,
            is_active=p.is_active,
            ai_scoring_enabled=p.ai_scoring_enabled,
            last_scraped_at=p.last_scraped_at,
            created_at=p.created_at,
            listing_count=counts.get(p.id, 0),
        )
        for p in projects
    ]
```

Modify the `get_project` endpoint to include listing count:

```python
@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = await _get_user_project(project_id, current_user, session)

    count_result = await session.execute(
        select(func.count(Listing.id)).where(Listing.project_id == project.id)
    )
    listing_count = count_result.scalar() or 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        filters=project.filters,
        scrape_url=project.scrape_url,
        is_active=project.is_active,
        ai_scoring_enabled=project.ai_scoring_enabled,
        last_scraped_at=project.last_scraped_at,
        created_at=project.created_at,
        listing_count=listing_count,
    )
```

Also update `create_project` and `update_project` return values to include `listing_count=0` (new projects) or a count query.

For `create_project`, before the `return project` line, replace with:

```python
    return ProjectResponse(
        id=project.id,
        name=project.name,
        filters=project.filters,
        scrape_url=project.scrape_url,
        is_active=project.is_active,
        ai_scoring_enabled=project.ai_scoring_enabled,
        last_scraped_at=project.last_scraped_at,
        created_at=project.created_at,
        listing_count=0,
    )
```

For `update_project`, replace the final `return project` with:

```python
    count_result = await session.execute(
        select(func.count(Listing.id)).where(Listing.project_id == project.id)
    )
    listing_count = count_result.scalar() or 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        filters=project.filters,
        scrape_url=project.scrape_url,
        is_active=project.is_active,
        ai_scoring_enabled=project.ai_scoring_enabled,
        last_scraped_at=project.last_scraped_at,
        created_at=project.created_at,
        listing_count=listing_count,
    )
```

- [ ] **Step 3: Run all tests**

Run: `cd backend && python3 -m pytest -v`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/project.py backend/app/api/projects.py
git commit -m "feat: add listing_count to ProjectResponse"
```

---

### Task 4: Frontend Scaffolding

**Files:**
- Create: `frontend/` directory with Vite + React + TypeScript setup
- Modify: `docker-compose.yml`

- [ ] **Step 1: Scaffold Vite project**

```bash
cd /mnt/d/Projects/Flatster
npm create vite@latest frontend -- --template react-ts
```

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install
npm install axios @tanstack/react-query react-router-dom recharts
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 3: Configure Tailwind**

Replace `frontend/src/index.css` with:

```css
@import "tailwindcss";
```

Add Tailwind plugin to `frontend/vite.config.ts`:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 4: Set up path aliases in tsconfig**

In `frontend/tsconfig.json` (or `tsconfig.app.json` if Vite created it), add to `compilerOptions`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

Install path resolution for Vite:

```bash
npm install -D vite-tsconfig-paths
```

Update `vite.config.ts` to add the plugin:

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineConfig({
  plugins: [react(), tailwindcss(), tsconfigPaths()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 5: Initialize shadcn/ui**

```bash
cd frontend
npx shadcn@latest init
```

When prompted, choose:
- Style: Default
- Base color: Neutral
- CSS variables: Yes

This creates `components.json` and `src/components/ui/` directory, and updates `tailwind.config.ts` and `src/index.css` with shadcn theme variables.

Then add the components we need:

```bash
npx shadcn@latest add button card dialog input label select tabs badge table toast separator switch dropdown-menu
```

- [ ] **Step 6: Add frontend to docker-compose.yml**

Add this service to `docker-compose.yml` after the `db` service:

```yaml
  frontend:
    image: node:20-alpine
    working_dir: /app
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: sh -c "npm install && npm run dev -- --host 0.0.0.0"
    depends_on:
      - app
```

- [ ] **Step 7: Verify dev server starts**

```bash
cd frontend && npm run dev
```

Expected: Vite dev server starts on port 5173.

- [ ] **Step 8: Commit**

```bash
cd /mnt/d/Projects/Flatster
git add frontend/ docker-compose.yml
git commit -m "feat: scaffold React frontend with Vite, Tailwind, shadcn/ui"
```

---

### Task 5: API Client and Auth Context

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/features/auth/AuthContext.tsx`
- Create: `frontend/src/lib/utils.ts`

- [ ] **Step 1: Create utility helpers**

Create `frontend/src/lib/utils.ts`:

```typescript
import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPrice(price: number | null | undefined): string {
  if (price == null) return "N/A"
  return new Intl.NumberFormat("sl-SI", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(price)
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return "N/A"
  return new Intl.DateTimeFormat("sl-SI", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(date))
}

export function formatRelativeTime(date: string | null | undefined): string {
  if (!date) return "Never"
  const now = new Date()
  const then = new Date(date)
  const diffMs = now.getTime() - then.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))

  if (diffHours < 1) return "Just now"
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}d ago`
  return formatDate(date)
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return "bg-gray-100 text-gray-600"
  if (score >= 70) return "bg-green-100 text-green-700"
  if (score >= 40) return "bg-yellow-100 text-yellow-700"
  return "bg-red-100 text-red-700"
}
```

Note: `cn()` may already exist if shadcn init created `lib/utils.ts`. If so, add the other functions to the existing file.

- [ ] **Step 2: Create API client**

Create `frontend/src/api/client.ts`:

```typescript
import axios from "axios"

const TOKEN_KEY = "flatster_token"

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      window.location.href = "/login"
    }
    return Promise.reject(error)
  }
)

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}
```

- [ ] **Step 3: Create AuthContext**

Create `frontend/src/features/auth/AuthContext.tsx`:

```tsx
import { createContext, useContext, useEffect, useState, type ReactNode } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { api, setToken, clearToken, getToken } from "@/api/client"

interface User {
  id: string
  email: string
  created_at: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setTokenState] = useState<string | null>(getToken())
  const [isLoading, setIsLoading] = useState(true)
  const queryClient = useQueryClient()

  useEffect(() => {
    if (token) {
      api
        .get("/auth/me")
        .then((res) => setUser(res.data))
        .catch(() => {
          clearToken()
          setTokenState(null)
        })
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [token])

  const login = async (email: string, password: string) => {
    const res = await api.post("/auth/login", { email, password })
    setToken(res.data.access_token)
    setTokenState(res.data.access_token)
    const userRes = await api.get("/auth/me")
    setUser(userRes.data)
  }

  const register = async (email: string, password: string) => {
    const res = await api.post("/auth/register", { email, password })
    setToken(res.data.access_token)
    setTokenState(res.data.access_token)
    const userRes = await api.get("/auth/me")
    setUser(userRes.data)
  }

  const logout = () => {
    clearToken()
    setTokenState(null)
    setUser(null)
    queryClient.clear()
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within AuthProvider")
  return ctx
}
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors (or only pre-existing template warnings).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/features/auth/AuthContext.tsx frontend/src/lib/utils.ts
git commit -m "feat: add API client, auth context, and utility helpers"
```

---

### Task 6: Constants and API Hooks

**Files:**
- Create: `frontend/src/lib/constants.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/api/projects.ts`
- Create: `frontend/src/api/listings.ts`
- Create: `frontend/src/api/favorites.ts`

- [ ] **Step 1: Create constants file**

Create `frontend/src/lib/constants.ts`:

```typescript
export const REGIONS: Record<string, string> = {
  "ljubljana-mesto": "LJ-mesto",
  "ljubljana-okolica": "LJ-okolica",
  "gorenjska": "Gorenjska",
  "juzna-primorska": "J. Primorska",
  "severna-primorska": "S. Primorska",
  "notranjska": "Notranjska",
  "savinjska": "Savinjska",
  "podravska": "Podravska",
  "koroska": "Koroška",
  "dolenjska": "Dolenjska",
  "posavska": "Posavska",
  "zasavska": "Zasavska",
  "pomurska": "Pomurska",
}

export const SUBREGIONS: Record<string, Record<string, string>> = {
  "ljubljana-mesto": {
    "lj-bezigrad": "Lj. Bežigrad",
    "lj-center": "Lj. Center",
    "lj-moste-polje": "Lj. Moste-Polje",
    "lj-siska": "Lj. Šiška",
    "lj-vic-rudnik": "Lj. Vič-Rudnik",
  },
  "ljubljana-okolica": {
    "domzale": "Domžale",
    "grosuplje": "Grosuplje",
    "kamnik": "Kamnik",
    "litija": "Litija",
    "lj-jz-del-vic-rudnik": "Lj. J&Z del (Vič, Rudnik)",
    "lj-sv-del-bezigrad": "Lj. SV del (Bežigrad)",
    "lj-sz-del-siska": "Lj. SZ del (Šiška)",
    "lj-v-del-moste-polje": "Lj. V del (Moste-Polje)",
    "logatec": "Logatec",
    "vrhnika": "Vrhnika",
  },
  "gorenjska": {
    "jesenice": "Jesenice",
    "kranj": "Kranj",
    "radovljica": "Radovljica",
    "skofja-loka": "Škofja Loka",
    "trzic": "Tržič",
  },
  "juzna-primorska": {
    "izola": "Izola",
    "koper": "Koper",
    "piran": "Piran",
    "sezana": "Sežana",
  },
  "severna-primorska": {
    "ajdovscina": "Ajdovščina",
    "idrija": "Idrija",
    "nova-gorica": "Nova Gorica",
    "tolmin": "Tolmin",
  },
  "notranjska": {
    "cerknica": "Cerknica",
    "ilirska-bistrica": "Ilirska Bistrica",
    "postojna": "Postojna",
  },
  "savinjska": {
    "celje": "Celje",
    "lasko": "Laško",
    "mozirje": "Mozirje",
    "slovenske-konjice": "Slovenske Konjice",
    "sentjur": "Šentjur",
    "smarje-pri-jelsah": "Šmarje pri Jelšah",
    "velenje": "Velenje",
    "zalec": "Žalec",
  },
  "podravska": {
    "lenart": "Lenart",
    "maribor": "Maribor",
    "ormoz": "Ormož",
    "pesnica": "Pesnica",
    "ptuj": "Ptuj",
    "ruse": "Ruše",
    "slovenska-bistrica": "Slovenska Bistrica",
  },
  "koroska": {
    "dravograd": "Dravograd",
    "radlje-ob-dravi": "Radlje ob Dravi",
    "ravne-na-koroskem": "Ravne na Koroškem",
    "slovenj-gradec": "Slovenj Gradec",
  },
  "dolenjska": {
    "crnomelj": "Črnomelj",
    "kocevje": "Kočevje",
    "metlika": "Metlika",
    "novo-mesto": "Novo mesto",
    "ribnica": "Ribnica",
    "trebnje": "Trebnje",
  },
  "posavska": {
    "brezice": "Brežice",
    "krsko": "Krško",
    "sevnica": "Sevnica",
  },
  "zasavska": {
    "hrastnik": "Hrastnik",
    "trbovlje": "Trbovlje",
    "zagorje-ob-savi": "Zagorje ob Savi",
  },
  "pomurska": {
    "gornja-radgona": "Gornja Radgona",
    "lendava": "Lendava",
    "ljutomer": "Ljutomer",
    "murska-sobota": "Murska Sobota",
  },
}

export const PROPERTY_TYPES: Record<string, string> = {
  "stanovanje": "Stanovanje",
  "hisa": "Hiša",
  "vikend": "Vikend",
  "posest": "Posest",
  "poslovni-prostor": "Poslovni prostor",
  "garaza": "Garaža",
  "pocitniski-objekt": "Počitniški objekt",
}

export const ROOM_TYPES: string[] = [
  "garsonjera",
  "1-sobno",
  "15-sobno",
  "2-sobno",
  "25-sobno",
  "3-sobno",
  "35-sobno",
  "4-sobno",
  "45-sobno",
  "5-in-vecsobno",
  "apartma",
  "soba",
]

export const TRANSACTION_TYPES = [
  { value: "prodaja", label: "Prodaja" },
  { value: "oddaja", label: "Oddaja" },
]
```

- [ ] **Step 2: Create API hooks — auth**

Create `frontend/src/api/auth.ts`:

```typescript
import { useMutation } from "@tanstack/react-query"
import { api } from "./client"

interface AuthResponse {
  access_token: string
  token_type: string
}

export function useLoginMutation() {
  return useMutation({
    mutationFn: async (data: { email: string; password: string }) => {
      const res = await api.post<AuthResponse>("/auth/login", data)
      return res.data
    },
  })
}

export function useRegisterMutation() {
  return useMutation({
    mutationFn: async (data: { email: string; password: string }) => {
      const res = await api.post<AuthResponse>("/auth/register", data)
      return res.data
    },
  })
}
```

- [ ] **Step 3: Create API hooks — projects**

Create `frontend/src/api/projects.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "./client"

export interface ProjectFilters {
  transaction: string
  region: string
  sub_region?: string | null
  property_type: string
  rooms?: string[] | null
  price_from?: number | null
  price_to?: number | null
  size_from?: number | null
  size_to?: number | null
  year_from?: number | null
  year_to?: number | null
}

export interface Project {
  id: string
  name: string
  filters: ProjectFilters
  scrape_url: string
  is_active: boolean
  ai_scoring_enabled: boolean
  last_scraped_at: string | null
  created_at: string
  listing_count: number
}

export interface ScrapeResult {
  listings_found: number
  new: number
  updated: number
  marked_sold: number
}

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: async () => {
      const res = await api.get<Project[]>("/projects")
      return res.data
    },
  })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: ["projects", id],
    queryFn: async () => {
      const res = await api.get<Project>(`/projects/${id}`)
      return res.data
    },
    enabled: !!id,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (data: { name: string; filters: ProjectFilters }) => {
      const res = await api.post<Project>("/projects", data)
      return res.data
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  })
}

export function useUpdateProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      id,
      ...data
    }: { id: string } & Partial<{ name: string; filters: ProjectFilters; is_active: boolean }>) => {
      const res = await api.patch<Project>(`/projects/${id}`, data)
      return res.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] })
      queryClient.invalidateQueries({ queryKey: ["projects", data.id] })
    },
  })
}

export function useDeleteProject() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/projects/${id}`)
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  })
}

export function useTriggerScrape() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await api.post<ScrapeResult>(`/projects/${id}/scrape`)
      return res.data
    },
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["projects", id] })
      queryClient.invalidateQueries({ queryKey: ["listings", id] })
    },
  })
}
```

- [ ] **Step 4: Create API hooks — listings**

Create `frontend/src/api/listings.ts`:

```typescript
import { useQuery } from "@tanstack/react-query"
import { api } from "./client"

export interface ListingSummary {
  id: string
  external_id: string
  url: string
  title: string
  location: string | null
  price: number | null
  price_per_m2: number | null
  size_m2: number | null
  rooms: string | null
  floor: string | null
  year_built: number | null
  status: string
  basic_score: number | null
  first_seen_at: string | null
  images: string[]
  thumbnail_url: string | null
}

export interface ListingDetail extends ListingSummary {
  description: string | null
  energy_class: string | null
  year_renovated: number | null
  land_size_m2: number | null
  agency: string | null
  ai_score: number | null
  ai_analysis: string | null
  price_history: { price: string; date: string }[]
  consecutive_misses: number
  last_seen_at: string | null
  marked_sold_at: string | null
  created_at: string
}

export interface PaginatedListings {
  items: ListingSummary[]
  total: number
  page: number
  per_page: number
}

export interface ListingFilters {
  status?: string
  min_price?: number
  max_price?: number
  min_size?: number
  max_size?: number
  sort_by?: string
  sort_order?: "asc" | "desc"
  page?: number
  per_page?: number
}

export function useListings(projectId: string, filters: ListingFilters = {}) {
  return useQuery({
    queryKey: ["listings", projectId, filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.status) params.set("status", filters.status)
      if (filters.min_price != null) params.set("min_price", String(filters.min_price))
      if (filters.max_price != null) params.set("max_price", String(filters.max_price))
      if (filters.min_size != null) params.set("min_size", String(filters.min_size))
      if (filters.max_size != null) params.set("max_size", String(filters.max_size))
      if (filters.sort_by) params.set("sort_by", filters.sort_by)
      if (filters.sort_order) params.set("sort_order", filters.sort_order)
      if (filters.page) params.set("page", String(filters.page))
      if (filters.per_page) params.set("per_page", String(filters.per_page))

      const res = await api.get<PaginatedListings>(
        `/projects/${projectId}/listings?${params.toString()}`
      )
      return res.data
    },
    enabled: !!projectId,
  })
}

export function useListing(projectId: string, listingId: string) {
  return useQuery({
    queryKey: ["listing", projectId, listingId],
    queryFn: async () => {
      const res = await api.get<ListingDetail>(
        `/projects/${projectId}/listings/${listingId}`
      )
      return res.data
    },
    enabled: !!projectId && !!listingId,
  })
}
```

- [ ] **Step 5: Create API hooks — favorites**

Create `frontend/src/api/favorites.ts`:

```typescript
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "./client"
import type { ListingSummary } from "./listings"

export function useFavorites() {
  return useQuery({
    queryKey: ["favorites"],
    queryFn: async () => {
      const res = await api.get<ListingSummary[]>("/favorites")
      return res.data
    },
  })
}

export function useToggleFavorite() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      listingId,
      isFavorited,
    }: {
      listingId: string
      isFavorited: boolean
    }) => {
      if (isFavorited) {
        await api.delete(`/favorites/${listingId}`)
      } else {
        await api.post(`/favorites/${listingId}`)
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["favorites"] })
    },
  })
}
```

- [ ] **Step 6: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/constants.ts frontend/src/api/
git commit -m "feat: add frontend constants and TanStack Query API hooks"
```

---

### Task 7: App Shell — Router, Layout, Protected Routes

**Files:**
- Create: `frontend/src/components/Layout.tsx`
- Create: `frontend/src/components/ProtectedRoute.tsx`
- Create: `frontend/src/components/LoadingSpinner.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`

- [ ] **Step 1: Create LoadingSpinner**

Create `frontend/src/components/LoadingSpinner.tsx`:

```tsx
export function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
    </div>
  )
}
```

- [ ] **Step 2: Create ProtectedRoute**

Create `frontend/src/components/ProtectedRoute.tsx`:

```tsx
import { Navigate } from "react-router-dom"
import { useAuth } from "@/features/auth/AuthContext"
import { LoadingSpinner } from "./LoadingSpinner"

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, isLoading } = useAuth()

  if (isLoading) return <LoadingSpinner />
  if (!token) return <Navigate to="/login" replace />

  return <>{children}</>
}
```

- [ ] **Step 3: Create Layout**

Create `frontend/src/components/Layout.tsx`:

```tsx
import { Link, Outlet, useNavigate } from "react-router-dom"
import { useAuth } from "@/features/auth/AuthContext"
import { useFavorites } from "@/api/favorites"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"

export function Layout() {
  const { user, logout } = useAuth()
  const { data: favorites } = useFavorites()
  const navigate = useNavigate()
  const favCount = favorites?.length ?? 0

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <nav className="flex items-center gap-6">
            <Link to="/projects" className="text-lg font-semibold">
              Flatster
            </Link>
            <Link
              to="/projects"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Projects
            </Link>
            <Link
              to="/compare"
              className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
            >
              Compare
              {favCount > 0 && (
                <Badge variant="secondary" className="ml-1">
                  {favCount}
                </Badge>
              )}
            </Link>
          </nav>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">{user?.email}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                logout()
                navigate("/login")
              }}
            >
              Logout
            </Button>
          </div>
        </div>
      </header>
      <main className="container mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
```

- [ ] **Step 4: Set up Router in App.tsx**

Replace `frontend/src/App.tsx`:

```tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { AuthProvider } from "@/features/auth/AuthContext"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { Layout } from "@/components/Layout"
import { LoginPage } from "@/features/auth/LoginPage"
import { ProjectsPage } from "@/features/projects/ProjectsPage"
import { ProjectDetailPage } from "@/features/projects/ProjectDetailPage"
import { ListingDetailPage } from "@/features/listings/ListingDetailPage"
import { ComparisonPage } from "@/features/listings/ComparisonPage"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/projects/:id" element={<ProjectDetailPage />} />
              <Route
                path="/projects/:id/listings/:listingId"
                element={<ListingDetailPage />}
              />
              <Route path="/compare" element={<ComparisonPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/projects" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
```

- [ ] **Step 5: Update main.tsx**

Replace `frontend/src/main.tsx`:

```tsx
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import App from "./App"
import "./index.css"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
```

Note: The page components (`LoginPage`, `ProjectsPage`, etc.) don't exist yet. Create placeholder files so TypeScript doesn't error. Each placeholder exports a simple component:

Create each of these files with a placeholder:

`frontend/src/features/auth/LoginPage.tsx`:
```tsx
export function LoginPage() {
  return <div>Login Page (TODO)</div>
}
```

`frontend/src/features/projects/ProjectsPage.tsx`:
```tsx
export function ProjectsPage() {
  return <div>Projects Page (TODO)</div>
}
```

`frontend/src/features/projects/ProjectDetailPage.tsx`:
```tsx
export function ProjectDetailPage() {
  return <div>Project Detail Page (TODO)</div>
}
```

`frontend/src/features/listings/ListingDetailPage.tsx`:
```tsx
export function ListingDetailPage() {
  return <div>Listing Detail Page (TODO)</div>
}
```

`frontend/src/features/listings/ComparisonPage.tsx`:
```tsx
export function ComparisonPage() {
  return <div>Comparison Page (TODO)</div>
}
```

- [ ] **Step 6: Verify TypeScript compiles and dev server runs**

Run: `cd frontend && npx tsc --noEmit && npm run dev`
Expected: Compiles clean, dev server starts.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat: add app shell with router, layout, and protected routes"
```

---

### Task 8: Login Page

**Files:**
- Modify: `frontend/src/features/auth/LoginPage.tsx`

- [ ] **Step 1: Implement LoginPage**

Replace `frontend/src/features/auth/LoginPage.tsx`:

```tsx
import { useState } from "react"
import { Navigate } from "react-router-dom"
import { useAuth } from "./AuthContext"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export function LoginPage() {
  const { token, login, register } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  if (token) return <Navigate to="/projects" replace />

  const handleSubmit = async (action: "login" | "register") => {
    setError("")
    setLoading(true)
    try {
      if (action === "login") {
        await login(email, password)
      } else {
        if (password.length < 8) {
          setError("Password must be at least 8 characters")
          setLoading(false)
          return
        }
        await register(email, password)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "An error occurred")
    } finally {
      setLoading(false)
    }
  }

  const form = (action: "login" | "register") => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor={`${action}-email`}>Email</Label>
        <Input
          id={`${action}-email`}
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor={`${action}-password`}>Password</Label>
        <Input
          id={`${action}-password`}
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={action === "register" ? "Min 8 characters" : ""}
        />
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button
        className="w-full"
        disabled={loading}
        onClick={() => handleSubmit(action)}
      >
        {loading ? "Loading..." : action === "login" ? "Login" : "Register"}
      </Button>
    </div>
  )

  return (
    <div className="flex min-h-screen items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center text-2xl">Flatster</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="login" onValueChange={() => setError("")}>
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="login">Login</TabsTrigger>
              <TabsTrigger value="register">Register</TabsTrigger>
            </TabsList>
            <TabsContent value="login">{form("login")}</TabsContent>
            <TabsContent value="register">{form("register")}</TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/auth/LoginPage.tsx
git commit -m "feat: add login/register page with tab toggle"
```

---

### Task 9: Projects Page and Create Dialog

**Files:**
- Modify: `frontend/src/features/projects/ProjectsPage.tsx`
- Create: `frontend/src/features/projects/ProjectCreateDialog.tsx`

- [ ] **Step 1: Create ProjectCreateDialog**

Create `frontend/src/features/projects/ProjectCreateDialog.tsx`:

```tsx
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useCreateProject, type ProjectFilters } from "@/api/projects"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  REGIONS,
  SUBREGIONS,
  PROPERTY_TYPES,
  ROOM_TYPES,
  TRANSACTION_TYPES,
} from "@/lib/constants"

export function ProjectCreateDialog() {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [transaction, setTransaction] = useState("prodaja")
  const [region, setRegion] = useState("")
  const [subRegion, setSubRegion] = useState("")
  const [propertyType, setPropertyType] = useState("stanovanje")
  const [rooms, setRooms] = useState<string[]>([])
  const [priceFrom, setPriceFrom] = useState("")
  const [priceTo, setPriceTo] = useState("")
  const [sizeFrom, setSizeFrom] = useState("")
  const [sizeTo, setSizeTo] = useState("")
  const [yearFrom, setYearFrom] = useState("")
  const [yearTo, setYearTo] = useState("")
  const [error, setError] = useState("")

  const createProject = useCreateProject()
  const navigate = useNavigate()

  const subRegions = region ? SUBREGIONS[region] || {} : {}
  const showRooms = propertyType === "stanovanje"

  const handleRoomToggle = (room: string) => {
    setRooms((prev) =>
      prev.includes(room) ? prev.filter((r) => r !== room) : [...prev, room]
    )
  }

  const handleSubmit = async () => {
    if (!name || !region) {
      setError("Name and region are required")
      return
    }

    const filters: ProjectFilters = {
      transaction,
      region,
      sub_region: subRegion || null,
      property_type: propertyType,
      rooms: showRooms && rooms.length > 0 ? rooms : null,
      price_from: priceFrom ? Number(priceFrom) : null,
      price_to: priceTo ? Number(priceTo) : null,
      size_from: sizeFrom ? Number(sizeFrom) : null,
      size_to: sizeTo ? Number(sizeTo) : null,
      year_from: yearFrom ? Number(yearFrom) : null,
      year_to: yearTo ? Number(yearTo) : null,
    }

    try {
      const project = await createProject.mutateAsync({ name, filters })
      setOpen(false)
      navigate(`/projects/${project.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create project")
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>New Project</Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Project</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="My search" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Transaction</Label>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={transaction}
                onChange={(e) => setTransaction(e.target.value)}
              >
                {TRANSACTION_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Property Type</Label>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={propertyType}
                onChange={(e) => {
                  setPropertyType(e.target.value)
                  if (e.target.value !== "stanovanje") setRooms([])
                }}
              >
                {Object.entries(PROPERTY_TYPES).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Region</Label>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={region}
                onChange={(e) => {
                  setRegion(e.target.value)
                  setSubRegion("")
                }}
              >
                <option value="">Select region...</option>
                {Object.entries(REGIONS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Sub-region (optional)</Label>
              <select
                className="w-full rounded-md border px-3 py-2 text-sm"
                value={subRegion}
                onChange={(e) => setSubRegion(e.target.value)}
                disabled={!region}
              >
                <option value="">All</option>
                {Object.entries(subRegions).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
          </div>

          {showRooms && (
            <div className="space-y-2">
              <Label>Rooms</Label>
              <div className="flex flex-wrap gap-2">
                {ROOM_TYPES.map((room) => (
                  <button
                    key={room}
                    type="button"
                    onClick={() => handleRoomToggle(room)}
                    className={`rounded-full border px-3 py-1 text-xs ${
                      rooms.includes(room)
                        ? "border-primary bg-primary text-primary-foreground"
                        : "hover:bg-muted"
                    }`}
                  >
                    {room}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Price from (EUR)</Label>
              <Input type="number" value={priceFrom} onChange={(e) => setPriceFrom(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Price to (EUR)</Label>
              <Input type="number" value={priceTo} onChange={(e) => setPriceTo(e.target.value)} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Size from (m2)</Label>
              <Input type="number" value={sizeFrom} onChange={(e) => setSizeFrom(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Size to (m2)</Label>
              <Input type="number" value={sizeTo} onChange={(e) => setSizeTo(e.target.value)} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Year from</Label>
              <Input type="number" value={yearFrom} onChange={(e) => setYearFrom(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Year to</Label>
              <Input type="number" value={yearTo} onChange={(e) => setYearTo(e.target.value)} />
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button className="w-full" onClick={handleSubmit} disabled={createProject.isPending}>
            {createProject.isPending ? "Creating..." : "Create Project"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 2: Implement ProjectsPage**

Replace `frontend/src/features/projects/ProjectsPage.tsx`:

```tsx
import { Link } from "react-router-dom"
import { useProjects } from "@/api/projects"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { LoadingSpinner } from "@/components/LoadingSpinner"
import { ProjectCreateDialog } from "./ProjectCreateDialog"
import { formatRelativeTime } from "@/lib/utils"

export function ProjectsPage() {
  const { data: projects, isLoading } = useProjects()

  if (isLoading) return <LoadingSpinner />

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Projects</h1>
        <ProjectCreateDialog />
      </div>

      {projects?.length === 0 && (
        <p className="text-muted-foreground">
          No projects yet. Create one to start tracking listings.
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {projects?.map((project) => (
          <Link key={project.id} to={`/projects/${project.id}`}>
            <Card className="transition-colors hover:bg-muted/50">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{project.name}</CardTitle>
                  <Badge variant={project.is_active ? "default" : "secondary"}>
                    {project.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="mb-2 truncate text-sm text-muted-foreground">
                  {project.scrape_url}
                </p>
                <div className="flex items-center justify-between text-sm">
                  <span>{project.listing_count} listings</span>
                  <span className="text-muted-foreground">
                    {formatRelativeTime(project.last_scraped_at)}
                  </span>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/projects/ProjectsPage.tsx frontend/src/features/projects/ProjectCreateDialog.tsx
git commit -m "feat: add projects dashboard and create dialog"
```

---

### Task 10: Listings Table and Favorite Button

**Files:**
- Create: `frontend/src/features/listings/FavoriteButton.tsx`
- Modify: `frontend/src/features/listings/ListingsTable.tsx` (create new, was placeholder)

- [ ] **Step 1: Create FavoriteButton**

Create `frontend/src/features/listings/FavoriteButton.tsx`:

```tsx
import { Star } from "lucide-react"
import { useFavorites, useToggleFavorite } from "@/api/favorites"
import { Button } from "@/components/ui/button"

export function FavoriteButton({ listingId }: { listingId: string }) {
  const { data: favorites } = useFavorites()
  const toggleFavorite = useToggleFavorite()

  const isFavorited = favorites?.some((f) => f.id === listingId) ?? false

  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-8 w-8"
      onClick={(e) => {
        e.preventDefault()
        e.stopPropagation()
        toggleFavorite.mutate({ listingId, isFavorited })
      }}
    >
      <Star
        className={`h-4 w-4 ${isFavorited ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground"}`}
      />
    </Button>
  )
}
```

Note: Install lucide-react if not already: `npm install lucide-react`

- [ ] **Step 2: Create ListingsTable**

Create `frontend/src/features/listings/ListingsTable.tsx`:

```tsx
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useListings, type ListingFilters } from "@/api/listings"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { LoadingSpinner } from "@/components/LoadingSpinner"
import { FavoriteButton } from "./FavoriteButton"
import { formatPrice, scoreColor } from "@/lib/utils"

interface Props {
  projectId: string
}

export function ListingsTable({ projectId }: Props) {
  const navigate = useNavigate()
  const [filters, setFilters] = useState<ListingFilters>({
    sort_by: "first_seen_at",
    sort_order: "desc",
    page: 1,
    per_page: 25,
  })

  const { data, isLoading } = useListings(projectId, filters)

  const handleSort = (column: string) => {
    setFilters((prev) => ({
      ...prev,
      sort_by: column,
      sort_order: prev.sort_by === column && prev.sort_order === "asc" ? "desc" : "asc",
      page: 1,
    }))
  }

  const sortIcon = (column: string) => {
    if (filters.sort_by !== column) return ""
    return filters.sort_order === "asc" ? " ↑" : " ↓"
  }

  if (isLoading) return <LoadingSpinner />

  const totalPages = Math.ceil((data?.total ?? 0) / (filters.per_page ?? 25))

  return (
    <div>
      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <select
          className="rounded-md border px-3 py-2 text-sm"
          value={filters.status || ""}
          onChange={(e) =>
            setFilters((prev) => ({ ...prev, status: e.target.value || undefined, page: 1 }))
          }
        >
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="sold">Sold</option>
          <option value="price_changed">Price changed</option>
        </select>
        <Input
          type="number"
          placeholder="Min price"
          className="w-32"
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              min_price: e.target.value ? Number(e.target.value) : undefined,
              page: 1,
            }))
          }
        />
        <Input
          type="number"
          placeholder="Max price"
          className="w-32"
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              max_price: e.target.value ? Number(e.target.value) : undefined,
              page: 1,
            }))
          }
        />
        <Input
          type="number"
          placeholder="Min size (m²)"
          className="w-32"
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              min_size: e.target.value ? Number(e.target.value) : undefined,
              page: 1,
            }))
          }
        />
        <Input
          type="number"
          placeholder="Max size (m²)"
          className="w-32"
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              max_size: e.target.value ? Number(e.target.value) : undefined,
              page: 1,
            }))
          }
        />
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="w-10 p-2"></th>
              <th className="p-2 text-left">Title</th>
              <th className="cursor-pointer p-2 text-right" onClick={() => handleSort("price")}>
                Price{sortIcon("price")}
              </th>
              <th className="cursor-pointer p-2 text-right" onClick={() => handleSort("price_per_m2")}>
                EUR/m²{sortIcon("price_per_m2")}
              </th>
              <th className="cursor-pointer p-2 text-right" onClick={() => handleSort("size_m2")}>
                Size{sortIcon("size_m2")}
              </th>
              <th className="p-2 text-center">Rooms</th>
              <th className="p-2 text-center">Floor</th>
              <th className="p-2 text-center">Year</th>
              <th className="cursor-pointer p-2 text-center" onClick={() => handleSort("basic_score")}>
                Score{sortIcon("basic_score")}
              </th>
              <th className="p-2 text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((listing) => (
              <tr
                key={listing.id}
                className="cursor-pointer border-b hover:bg-muted/50"
                onClick={() => navigate(`/projects/${projectId}/listings/${listing.id}`)}
              >
                <td className="p-2">
                  <FavoriteButton listingId={listing.id} />
                </td>
                <td className="max-w-xs truncate p-2">{listing.title}</td>
                <td className="p-2 text-right">{formatPrice(listing.price)}</td>
                <td className="p-2 text-right">
                  {listing.price_per_m2 ? `${Math.round(listing.price_per_m2)}` : "—"}
                </td>
                <td className="p-2 text-right">
                  {listing.size_m2 ? `${listing.size_m2} m²` : "—"}
                </td>
                <td className="p-2 text-center">{listing.rooms || "—"}</td>
                <td className="p-2 text-center">{listing.floor || "—"}</td>
                <td className="p-2 text-center">{listing.year_built || "—"}</td>
                <td className="p-2 text-center">
                  {listing.basic_score != null ? (
                    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${scoreColor(listing.basic_score)}`}>
                      {Math.round(listing.basic_score)}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="p-2 text-center">
                  <Badge
                    variant={
                      listing.status === "active"
                        ? "default"
                        : listing.status === "sold"
                          ? "destructive"
                          : "secondary"
                    }
                  >
                    {listing.status}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            {data?.total} listings total
          </span>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={(filters.page ?? 1) <= 1}
              onClick={() => setFilters((prev) => ({ ...prev, page: (prev.page ?? 1) - 1 }))}
            >
              Previous
            </Button>
            <span className="text-sm">
              Page {filters.page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={(filters.page ?? 1) >= totalPages}
              onClick={() => setFilters((prev) => ({ ...prev, page: (prev.page ?? 1) + 1 }))}
            >
              Next
            </Button>
            <select
              className="rounded-md border px-2 py-1 text-sm"
              value={filters.per_page}
              onChange={(e) =>
                setFilters((prev) => ({ ...prev, per_page: Number(e.target.value), page: 1 }))
              }
            >
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/listings/FavoriteButton.tsx frontend/src/features/listings/ListingsTable.tsx
git commit -m "feat: add listings table with filters, sorting, and pagination"
```

---

### Task 11: Project Detail Page and Settings Panel

**Files:**
- Modify: `frontend/src/features/projects/ProjectDetailPage.tsx`
- Create: `frontend/src/features/projects/ProjectSettingsPanel.tsx`

- [ ] **Step 1: Create ProjectSettingsPanel**

Create `frontend/src/features/projects/ProjectSettingsPanel.tsx`:

```tsx
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useDeleteProject, useTriggerScrape, useUpdateProject, type Project } from "@/api/projects"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { formatRelativeTime } from "@/lib/utils"
import { REGIONS, PROPERTY_TYPES } from "@/lib/constants"

interface Props {
  project: Project
}

export function ProjectSettingsPanel({ project }: Props) {
  const navigate = useNavigate()
  const updateProject = useUpdateProject()
  const deleteProject = useDeleteProject()
  const triggerScrape = useTriggerScrape()
  const [scrapeResult, setScrapeResult] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const handleScrape = async () => {
    setScrapeResult(null)
    try {
      const result = await triggerScrape.mutateAsync(project.id)
      setScrapeResult(
        `Found ${result.listings_found}: ${result.new} new, ${result.updated} updated, ${result.marked_sold} sold`
      )
    } catch {
      setScrapeResult("Scrape failed")
    }
  }

  const handleDelete = async () => {
    await deleteProject.mutateAsync(project.id)
    navigate("/projects")
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">{project.name}</h2>

      <div className="space-y-2 text-sm">
        <div>
          <span className="text-muted-foreground">Region: </span>
          {REGIONS[project.filters.region] || project.filters.region}
        </div>
        <div>
          <span className="text-muted-foreground">Type: </span>
          {PROPERTY_TYPES[project.filters.property_type] || project.filters.property_type}
        </div>
        <div>
          <span className="text-muted-foreground">Transaction: </span>
          {project.filters.transaction}
        </div>
        {project.filters.rooms && (
          <div>
            <span className="text-muted-foreground">Rooms: </span>
            {project.filters.rooms.join(", ")}
          </div>
        )}
        <div>
          <span className="text-muted-foreground">Listings: </span>
          {project.listing_count}
        </div>
        <div>
          <span className="text-muted-foreground">Last scraped: </span>
          {formatRelativeTime(project.last_scraped_at)}
        </div>
      </div>

      <Separator />

      <div className="flex items-center gap-2">
        <Switch
          checked={project.is_active}
          onCheckedChange={(checked) =>
            updateProject.mutate({ id: project.id, is_active: checked })
          }
        />
        <Label>Active</Label>
      </div>

      <Separator />

      <Button
        className="w-full"
        onClick={handleScrape}
        disabled={triggerScrape.isPending}
      >
        {triggerScrape.isPending ? "Scraping..." : "Scrape Now"}
      </Button>
      {scrapeResult && (
        <p className="text-sm text-muted-foreground">{scrapeResult}</p>
      )}

      <Separator />

      {!confirmDelete ? (
        <Button
          variant="destructive"
          className="w-full"
          onClick={() => setConfirmDelete(true)}
        >
          Delete Project
        </Button>
      ) : (
        <div className="space-y-2">
          <p className="text-sm text-destructive">Are you sure? This deletes all listings.</p>
          <div className="flex gap-2">
            <Button variant="destructive" className="flex-1" onClick={handleDelete}>
              Confirm
            </Button>
            <Button variant="outline" className="flex-1" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Implement ProjectDetailPage**

Replace `frontend/src/features/projects/ProjectDetailPage.tsx`:

```tsx
import { useParams } from "react-router-dom"
import { useProject } from "@/api/projects"
import { LoadingSpinner } from "@/components/LoadingSpinner"
import { ListingsTable } from "@/features/listings/ListingsTable"
import { ProjectSettingsPanel } from "./ProjectSettingsPanel"

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: project, isLoading } = useProject(id!)

  if (isLoading || !project) return <LoadingSpinner />

  return (
    <div className="flex gap-6">
      <div className="flex-1">
        <h1 className="mb-4 text-2xl font-bold">{project.name}</h1>
        <ListingsTable projectId={project.id} />
      </div>
      <div className="w-80 shrink-0">
        <ProjectSettingsPanel project={project} />
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/projects/ProjectDetailPage.tsx frontend/src/features/projects/ProjectSettingsPanel.tsx
git commit -m "feat: add project detail page with settings panel"
```

---

### Task 12: Listing Detail Page with Price Chart

**Files:**
- Create: `frontend/src/features/listings/PriceHistoryChart.tsx`
- Modify: `frontend/src/features/listings/ListingDetailPage.tsx`

- [ ] **Step 1: Create PriceHistoryChart**

Create `frontend/src/features/listings/PriceHistoryChart.tsx`:

```tsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

interface PriceEntry {
  price: string
  date: string
}

export function PriceHistoryChart({ history }: { history: PriceEntry[] }) {
  if (history.length === 0) return null

  const data = history.map((entry) => ({
    date: entry.date,
    price: Number(entry.price),
  }))

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <XAxis dataKey="date" tick={{ fontSize: 12 }} />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            formatter={(value: number) =>
              new Intl.NumberFormat("sl-SI", {
                style: "currency",
                currency: "EUR",
              }).format(value)
            }
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={data.length === 1}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 2: Implement ListingDetailPage**

Replace `frontend/src/features/listings/ListingDetailPage.tsx`:

```tsx
import { useParams, useNavigate } from "react-router-dom"
import { useListing } from "@/api/listings"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { LoadingSpinner } from "@/components/LoadingSpinner"
import { FavoriteButton } from "./FavoriteButton"
import { PriceHistoryChart } from "./PriceHistoryChart"
import { formatPrice, formatDate, scoreColor } from "@/lib/utils"

export function ListingDetailPage() {
  const { id, listingId } = useParams<{ id: string; listingId: string }>()
  const navigate = useNavigate()
  const { data: listing, isLoading } = useListing(id!, listingId!)

  if (isLoading || !listing) return <LoadingSpinner />

  return (
    <div className="mx-auto max-w-4xl">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <Button variant="ghost" size="sm" onClick={() => navigate(`/projects/${id}`)}>
            ← Back
          </Button>
          <h1 className="mt-2 text-2xl font-bold">{listing.title}</h1>
          {listing.location && (
            <p className="text-muted-foreground">{listing.location}</p>
          )}
        </div>
        <FavoriteButton listingId={listing.id} />
      </div>

      {/* Key facts + Score */}
      <div className="mb-6 grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-3">
          <div className="text-3xl font-bold">{formatPrice(listing.price)}</div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div><span className="text-muted-foreground">Price/m²:</span> {listing.price_per_m2 ? `${Math.round(listing.price_per_m2)} EUR` : "N/A"}</div>
            <div><span className="text-muted-foreground">Size:</span> {listing.size_m2 ? `${listing.size_m2} m²` : "N/A"}</div>
            <div><span className="text-muted-foreground">Rooms:</span> {listing.rooms || "N/A"}</div>
            <div><span className="text-muted-foreground">Floor:</span> {listing.floor || "N/A"}</div>
            <div><span className="text-muted-foreground">Year built:</span> {listing.year_built || "N/A"}</div>
            <div><span className="text-muted-foreground">Renovated:</span> {listing.year_renovated || "N/A"}</div>
            <div><span className="text-muted-foreground">Energy class:</span> {listing.energy_class || "N/A"}</div>
            <div><span className="text-muted-foreground">Agency:</span> {listing.agency || "N/A"}</div>
          </div>
          <Badge
            variant={
              listing.status === "active"
                ? "default"
                : listing.status === "sold"
                  ? "destructive"
                  : "secondary"
            }
          >
            {listing.status}
          </Badge>
        </div>
        <div className="flex flex-col items-center justify-center rounded-lg border p-4">
          <span className="text-sm text-muted-foreground">Score</span>
          {listing.basic_score != null ? (
            <span className={`mt-1 rounded-lg px-4 py-2 text-3xl font-bold ${scoreColor(listing.basic_score)}`}>
              {Math.round(listing.basic_score)}
            </span>
          ) : (
            <span className="mt-1 text-2xl text-muted-foreground">—</span>
          )}
          <span className="mt-3 text-xs text-muted-foreground">AI Score (Phase 4)</span>
          <span className="text-lg text-muted-foreground">—</span>
        </div>
      </div>

      {/* Images */}
      {listing.images.length > 0 && (
        <>
          <Separator className="my-6" />
          <h2 className="mb-3 text-lg font-semibold">Images</h2>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {listing.images.map((img, i) => (
              <img
                key={i}
                src={img}
                alt={`Image ${i + 1}`}
                className="h-48 w-auto shrink-0 rounded-md object-cover"
                loading="lazy"
              />
            ))}
          </div>
        </>
      )}

      {/* Price History */}
      {listing.price_history.length > 0 && (
        <>
          <Separator className="my-6" />
          <h2 className="mb-3 text-lg font-semibold">Price History</h2>
          <PriceHistoryChart history={listing.price_history} />
        </>
      )}

      {/* Description */}
      {listing.description && (
        <>
          <Separator className="my-6" />
          <h2 className="mb-3 text-lg font-semibold">Description</h2>
          <p className="whitespace-pre-wrap text-sm">{listing.description}</p>
        </>
      )}

      {/* Footer */}
      <Separator className="my-6" />
      <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
        <a href={listing.url} target="_blank" rel="noopener noreferrer" className="underline">
          View on nepremicnine.net
        </a>
        <span>First seen: {formatDate(listing.first_seen_at)}</span>
        <span>Last seen: {formatDate(listing.last_seen_at)}</span>
        <span>Misses: {listing.consecutive_misses}</span>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/listings/ListingDetailPage.tsx frontend/src/features/listings/PriceHistoryChart.tsx
git commit -m "feat: add listing detail page with price history chart"
```

---

### Task 13: Comparison Page

**Files:**
- Modify: `frontend/src/features/listings/ComparisonPage.tsx`

- [ ] **Step 1: Implement ComparisonPage**

Replace `frontend/src/features/listings/ComparisonPage.tsx`:

```tsx
import { useFavorites } from "@/api/favorites"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { LoadingSpinner } from "@/components/LoadingSpinner"
import { FavoriteButton } from "./FavoriteButton"
import { formatPrice, scoreColor } from "@/lib/utils"

export function ComparisonPage() {
  const { data: favorites, isLoading } = useFavorites()

  if (isLoading) return <LoadingSpinner />

  if (!favorites || favorites.length === 0) {
    return (
      <div className="py-12 text-center">
        <h1 className="mb-2 text-2xl font-bold">Compare Listings</h1>
        <p className="text-muted-foreground">
          No favorites yet. Star listings from any project to compare them here.
        </p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Compare Listings ({favorites.length})</h1>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {favorites.map((listing) => (
          <Card key={listing.id}>
            {listing.thumbnail_url && (
              <img
                src={listing.thumbnail_url}
                alt={listing.title}
                className="h-40 w-full rounded-t-lg object-cover"
              />
            )}
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <CardTitle className="line-clamp-2 text-sm">{listing.title}</CardTitle>
                <FavoriteButton listingId={listing.id} />
              </div>
              {listing.location && (
                <p className="text-xs text-muted-foreground">{listing.location}</p>
              )}
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="text-lg font-bold">{formatPrice(listing.price)}</div>
              <div className="grid grid-cols-2 gap-1 text-xs">
                <span>EUR/m²: {listing.price_per_m2 ? Math.round(listing.price_per_m2) : "—"}</span>
                <span>Size: {listing.size_m2 ? `${listing.size_m2} m²` : "—"}</span>
                <span>Rooms: {listing.rooms || "—"}</span>
                <span>Floor: {listing.floor || "—"}</span>
                <span>Year: {listing.year_built || "—"}</span>
                <span>
                  Score:{" "}
                  {listing.basic_score != null ? (
                    <span className={`rounded px-1 ${scoreColor(listing.basic_score)}`}>
                      {Math.round(listing.basic_score)}
                    </span>
                  ) : (
                    "—"
                  )}
                </span>
              </div>
              <Badge
                variant={
                  listing.status === "active"
                    ? "default"
                    : listing.status === "sold"
                      ? "destructive"
                      : "secondary"
                }
              >
                {listing.status}
              </Badge>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npx tsc --noEmit`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/listings/ComparisonPage.tsx
git commit -m "feat: add comparison page for favorited listings"
```

---

### Task 14: Verify Full Build and Run

**Files:** None (verification only)

- [ ] **Step 1: Run TypeScript check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 2: Run Vite build**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Run backend tests**

Run: `cd backend && python3 -m pytest -v`
Expected: All tests pass (77+ with new favorites code).

- [ ] **Step 4: Test dev server**

Run: `cd frontend && npm run dev`
Navigate to `http://localhost:5173`. Expected: App loads, shows login page.

If any step fails, fix before proceeding.
