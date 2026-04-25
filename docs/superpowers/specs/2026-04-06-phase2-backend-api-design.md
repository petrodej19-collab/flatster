# Phase 2: Backend API — Design Spec

**Project:** NepremicnineTracker
**Date:** 2026-04-06
**Scope:** Authentication, project CRUD, listings API, scraper-to-DB sync, basic scoring, scheduler

---

## 1. Overview

Phase 2 adds the full backend API on top of the Phase 1 foundation (scraper, models, database). It provides JWT authentication with multi-user registration, project CRUD with scrape triggering, paginated listing endpoints, a sync service that bridges scraped data to the database (with price tracking and sold detection), multi-factor investment scoring, and APScheduler-based automatic scraping.

### Phases roadmap

- **Phase 1 (done):** Foundation + Scraper
- **Phase 2 (this spec):** Backend API
- **Phase 3:** React frontend
- **Phase 4:** AI scoring + polish

---

## 2. Project Structure

New and modified files:

```
backend/app/
    main.py                  # (modified) Add router includes, lifespan with scheduler
    config.py                # (modified) Add JWT, scheduler, sold detection settings
    api/
        __init__.py
        auth.py              # POST /register, POST /login, GET /me
        projects.py          # CRUD, POST /{id}/scrape
        listings.py          # GET with filters, GET /{id}
        deps.py              # get_current_user dependency
    services/
        __init__.py
        auth.py              # hash_password, verify_password, create_token, decode_token
        scraper_sync.py      # Upsert listings into DB, price tracking, sold detection
        scoring.py           # Multi-factor basic scoring
    scheduler.py             # APScheduler setup, register/unregister project jobs
    schemas/
        auth.py              # LoginRequest, RegisterRequest, TokenResponse, UserResponse
        project.py           # ProjectCreate, ProjectUpdate, ProjectResponse
        listing.py           # ListingSummary, ListingDetail, ListingFilters, PaginatedListings
```

Existing files untouched: all `scraper/` modules, `models/`, `database.py`, `schemas/scraper.py`.

---

## 3. Configuration Additions

New settings in `config.py`:

```python
# Auth
JWT_SECRET: str = "change-me-in-production"
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

# Scheduler
SCHEDULE_INTERVAL_HOURS: float = 6.0

# Sold detection
SOLD_DETECTION_MISSES: int = 3
```

`JWT_SECRET` must be overridden in `.env` for any real deployment. The default is intentionally obvious to flag misconfiguration.

---

## 4. Authentication

### 4.1 Service layer (`services/auth.py`)

- `hash_password(plain: str) -> str` — bcrypt hash
- `verify_password(plain: str, hashed: str) -> bool` — bcrypt verify
- `create_access_token(user_id: UUID) -> str` — JWT with `sub` claim (user UUID as string), `exp` claim
- `decode_access_token(token: str) -> UUID` — validates and returns user UUID, raises on expiry/invalid

### 4.2 Dependency (`api/deps.py`)

- `get_current_user(token, session)` — extracts Bearer token from `Authorization` header via FastAPI's `OAuth2PasswordBearer`, decodes it, fetches the User from DB. Returns User or raises 401.

### 4.3 Router (`api/auth.py`)

**`POST /api/auth/register`**
- Body: `{"email": str, "password": str}`
- Creates a new user with bcrypt-hashed password
- Returns: `{"access_token": str, "token_type": "bearer"}` (auto-login on registration)
- 409 on duplicate email

**`POST /api/auth/login`**
- Body: `{"email": str, "password": str}`
- Verifies credentials against DB
- Returns: `{"access_token": str, "token_type": "bearer"}`
- 401 on invalid credentials

**`GET /api/auth/me`**
- Requires auth
- Returns: `{"id": uuid, "email": str, "created_at": datetime}`

### 4.4 Schemas (`schemas/auth.py`)

```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str  # min_length=8

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    id: UUID
    email: str
    created_at: datetime
```

### 4.5 New dependencies

- `passlib[bcrypt]>=1.7.0` — password hashing
- `python-jose[cryptography]>=3.3.0` — JWT encode/decode

---

## 5. Project CRUD

### 5.1 Router (`api/projects.py`)

All endpoints require auth. Projects are scoped to the current user.

**`POST /api/projects`**
- Body: `{"name": str, "filters": ProjectFilters, "is_active": bool = true, "ai_scoring_enabled": bool = false}`
- Validates filters (existing ProjectFilters validation handles this)
- Builds `scrape_url` from filters via `build_scrape_url()`
- Creates project in DB, registers scheduler job if `is_active`
- Returns: ProjectResponse

**`GET /api/projects`**
- Returns all projects for the current user
- Returns: `list[ProjectResponse]`

**`GET /api/projects/{id}`**
- Returns single project (404 if not found or not owned by user)
- Returns: ProjectResponse

**`PATCH /api/projects/{id}`**
- Body: any subset of `{"name", "filters", "is_active", "ai_scoring_enabled"}`
- If `filters` changes, rebuilds `scrape_url`
- If `is_active` changes, registers/unregisters scheduler job accordingly
- Returns: ProjectResponse

**`DELETE /api/projects/{id}`**
- Deletes project and all its listings (cascade)
- Unregisters scheduler job
- Returns: 204

**`POST /api/projects/{id}/scrape`**
- Triggers an immediate scrape for this project
- Runs the scraper, syncs results to DB (via `scraper_sync` service)
- Returns: `{"listings_found": int, "new": int, "updated": int, "marked_sold": int}`

### 5.2 Schemas (`schemas/project.py`)

```python
class ProjectCreate(BaseModel):
    name: str
    filters: ProjectFilters
    is_active: bool = True
    ai_scoring_enabled: bool = False

class ProjectUpdate(BaseModel):
    name: str | None = None
    filters: ProjectFilters | None = None
    is_active: bool | None = None
    ai_scoring_enabled: bool | None = None

class ProjectResponse(BaseModel):
    id: UUID
    name: str
    filters: dict  # serialized ProjectFilters
    scrape_url: str
    is_active: bool
    ai_scoring_enabled: bool
    last_scraped_at: datetime | None
    created_at: datetime
```

---

## 6. Listings API

### 6.1 Router (`api/listings.py`)

All endpoints require auth. Listings are accessed through their parent project (ownership verified).

**`GET /api/projects/{project_id}/listings`**
- Query params:
  - `status`: filter by "active", "sold", "price_changed" (optional)
  - `min_price` / `max_price`: price range (optional)
  - `min_size` / `max_size`: size range (optional)
  - `sort_by`: "price", "size_m2", "basic_score", "first_seen_at", "price_per_m2" (default: "first_seen_at")
  - `sort_order`: "asc" / "desc" (default: "desc")
  - `page`: page number (default: 1)
  - `per_page`: items per page (default: 25, max: 100)
- Returns: `{"items": list[ListingSummary], "total": int, "page": int, "per_page": int}`

**`GET /api/projects/{project_id}/listings/{listing_id}`**
- Returns full listing detail including description, images, price_history, scores
- Returns: ListingDetail

### 6.2 Schemas (`schemas/listing.py`)

```python
class ListingSummary(BaseModel):
    id: UUID
    external_id: str
    url: str
    title: str
    location: str | None
    price: Decimal | None
    price_per_m2: Decimal | None
    size_m2: Decimal | None
    rooms: str | None
    floor: str | None
    year_built: int | None
    status: str
    basic_score: Decimal | None
    thumbnail_url: str | None  # first image from images array
    first_seen_at: datetime | None

class ListingDetail(ListingSummary):
    description: str | None
    images: list[str]
    energy_class: str | None
    year_renovated: int | None
    land_size_m2: Decimal | None
    agency: str | None
    ai_score: Decimal | None
    ai_analysis: str | None
    price_history: list[dict]
    consecutive_misses: int
    last_seen_at: datetime | None
    marked_sold_at: datetime | None
    created_at: datetime

class PaginatedListings(BaseModel):
    items: list[ListingSummary]
    total: int
    page: int
    per_page: int
```

`ListingSummary` is the lightweight version for list views — pulls `thumbnail_url` from the first entry of the `images` JSONB array. `ListingDetail` extends it with everything.

---

## 7. Scraper Sync Service

The core logic that bridges scraper output and the database. Called after every scrape run (manual or scheduled).

### 7.1 Service (`services/scraper_sync.py`)

**`async def sync_scraped_listings(session, project_id, scraped: list[ScrapedListing], scrape_complete: bool) -> SyncResult`**

For each scraped listing:
1. Look up existing listing by `(project_id, external_id)`
2. **New listing** — insert with `status="active"`, `first_seen_at=now()`, `last_seen_at=now()`, initial `price_history=[{"price": X, "date": "YYYY-MM-DD"}]`
3. **Existing listing, same price** — update `last_seen_at=now()`, reset `consecutive_misses=0`
4. **Existing listing, price changed** — update `last_seen_at=now()`, reset `consecutive_misses=0`, set `status="price_changed"`, append new entry to `price_history`

After processing all scraped listings (only if `scrape_complete=True`):
5. **Missing listings** — for active/price_changed listings in this project that were NOT in the scraped batch: increment `consecutive_misses`
6. **Sold detection** — if `consecutive_misses >= settings.SOLD_DETECTION_MISSES`, set `status="sold"`, `marked_sold_at=now()`

After sync:
7. **Trigger scoring** — call `score_project_listings(session, project_id)` to recalculate basic scores

### 7.2 Return value

```python
@dataclass
class SyncResult:
    listings_found: int
    new: int
    updated: int
    marked_sold: int
```

### 7.3 Partial scrape safety

If a scrape only gets page 1 (e.g., pagination failed), we'd incorrectly mark everything on later pages as "missed". The scraper already logs how many pages it expected vs. fetched. We pass `scrape_complete: bool` to `sync_scraped_listings` — if `False`, skip the missing-listing detection step entirely. Only increment `consecutive_misses` when the scrape was complete.

---

## 8. Basic Scoring

### 8.1 Service (`services/scoring.py`)

**`async def score_project_listings(session, project_id) -> None`**

Calculates a 0-100 score for each active listing in the project. Score is a weighted sum of normalized factors.

### 8.2 Factors and weights

| Factor | Weight | Logic |
|---|---|---|
| Price/m2 vs project average | 40% | Lower is better. 0 = 2x average, 50 = at average, 100 = half average or less. Linear interpolation. |
| Year built/renovated | 25% | Uses `max(year_built, year_renovated)` if available. 100 = 2020+, scales down linearly, 0 = pre-1950. |
| Size | 15% | Larger is better relative to project average. 100 = 2x average, 50 = at average, 0 = half or less. |
| Energy class | 10% | A1/A2 = 100, B1/B2 = 80, C = 60, D = 40, E = 20, F/G = 0. Null = 50 (neutral). |
| Floor | 10% | Middle floors score highest (100), ground floor = 60, top floor = 80. Null = 50. |

### 8.3 Design choices

- Scores are **relative to the project** — a "good deal" is relative to what else is available with the same filters
- Recalculated after every sync — averages shift as listings come and go
- Listings missing a factor (e.g., no price) get 50 (neutral) for that factor, so they aren't unfairly penalized or boosted
- Weights are hardcoded constants in `scoring.py` — not configurable via API

---

## 9. Scheduler

### 9.1 Module (`scheduler.py`)

Uses APScheduler 3.x `AsyncIOScheduler` with an in-memory job store.

**`init_scheduler(session_factory) -> AsyncIOScheduler`**
- Creates scheduler instance
- On app startup: queries all active projects from DB, registers a job for each
- Returns the scheduler

**`register_project_job(scheduler, project_id)`**
- Adds an interval job: runs `_run_project_scrape(project_id)` every `settings.SCHEDULE_INTERVAL_HOURS` hours
- Job ID = `f"scrape_{project_id}"` for easy lookup
- Jitter of +/- 10 minutes to avoid all projects scraping simultaneously

**`unregister_project_job(scheduler, project_id)`**
- Removes the job by ID. No-op if job doesn't exist.

**`async def _run_project_scrape(project_id)`**
- Opens a fresh DB session
- Loads project, gets filters
- Calls `scrape_project(filters, settings)` from the Phase 1 scraper
- Calls `sync_scraped_listings(session, project_id, results)`
- Updates `project.last_scraped_at`
- All wrapped in try/except — a failed scrape logs the error but never crashes the scheduler

### 9.2 Lifecycle (in `main.py`)

```python
@asynccontextmanager
async def lifespan(app):
    scheduler = await init_scheduler(async_session)
    app.state.scheduler = scheduler
    scheduler.start()
    yield
    scheduler.shutdown()
```

Routers access the scheduler via `request.app.state.scheduler` when they need to register/unregister jobs on project create/update/delete.

### 9.3 New dependency

- `apscheduler>=3.10.0,<4.0` — APScheduler 3.x (stable async support, not 4.x which has a different API)

---

## 10. Route Mounting

```python
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(listings_router, prefix="/api/projects", tags=["listings"])
```

Listings router mounted under `/api/projects` since all listing endpoints are project-scoped.

Health check stays at `GET /health`.

---

## 11. Error Handling

Standard FastAPI `HTTPException` usage:
- 401: invalid/missing token, wrong credentials
- 403: accessing another user's project
- 404: project/listing not found
- 409: duplicate email on registration
- 422: validation errors (handled by Pydantic automatically)

No custom exception handlers — FastAPI's defaults are sufficient.

---

## 12. New Dependencies Summary

Added to `requirements.txt`:

```
passlib[bcrypt]>=1.7.0
python-jose[cryptography]>=3.3.0
apscheduler>=3.10.0,<4.0
```

---

## 13. Testing Strategy

### Unit tests (no browser, no network, no DB)

- **test_auth_service.py** — hash/verify passwords, create/decode tokens, expired token handling
- **test_scoring.py** — scoring logic with known inputs, edge cases (missing fields, single listing)
- **test_scraper_sync.py** — sync logic with mocked DB session: new listings, price changes, sold detection, partial scrape handling

### Integration tests (needs running DB)

- **test_auth_api.py** — register, login, /me, duplicate email, bad credentials
- **test_projects_api.py** — CRUD operations, ownership scoping, scrape trigger
- **test_listings_api.py** — pagination, filtering, sorting, detail endpoint

Integration tests use `pytest-asyncio` + a test database (separate from dev). Marked with `@pytest.mark.integration`.

---

## 14. Out of Scope for Phase 2

- Frontend (Phase 3)
- AI scoring via Claude API (Phase 4)
- Email notifications or alerts
- Listing comparisons or favoriting
- Export functionality (CSV, PDF)
- Rate limiting on API endpoints
- Password reset flow
