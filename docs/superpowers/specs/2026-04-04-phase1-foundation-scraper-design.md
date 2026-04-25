# Phase 1: Foundation + Scraper — Design Spec

**Project:** NepremicnineTracker
**Date:** 2026-04-04
**Scope:** Project structure, Docker, database models, Playwright scraper, URL builder, constants

---

## 1. Overview

Phase 1 establishes the project foundation and builds a working scraper for nepremicnine.net. The scraper extracts apartment listing data using Playwright (headless Chromium) since the site returns 403 for simple HTTP requests. No API endpoints, no auth, no frontend — just infrastructure and a reliable scraper that returns structured data.

### Phases roadmap

- **Phase 1 (this spec):** Foundation + Scraper
- **Phase 2:** Backend API (auth, project CRUD, listings, basic scoring, scheduler)
- **Phase 3:** React frontend
- **Phase 4:** AI scoring + polish

---

## 2. Project Structure

```
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app (health check only in Phase 1)
│   │   ├── config.py            # pydantic-settings, loads .env
│   │   ├── database.py          # Async SQLAlchemy engine + session factory
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # DeclarativeBase
│   │   │   ├── user.py          # User model
│   │   │   ├── project.py       # Project model
│   │   │   └── listing.py       # Listing model
│   │   ├── scraper/
│   │   │   ├── __init__.py
│   │   │   ├── browser.py       # Playwright browser lifecycle
│   │   │   ├── url_builder.py   # build_scrape_url(filters) -> URL
│   │   │   ├── list_parser.py   # Parse listing cards from search results
│   │   │   ├── detail_parser.py # Parse individual listing detail pages
│   │   │   ├── scraper.py       # Orchestrator: paginate -> parse -> visit details
│   │   │   └── constants.py     # Region/sub-region mapping, room types, property types
│   │   └── schemas/
│   │       ├── __init__.py
│   │       └── scraper.py       # ScrapedListing pydantic model
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── tests/
│       ├── __init__.py
│       ├── fixtures/            # Saved HTML snapshots for parser tests
│       ├── test_url_builder.py
│       ├── test_list_parser.py
│       ├── test_detail_parser.py
│       └── test_scraper.py
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── .gitignore
```

---

## 3. Docker Setup

### docker-compose.yml

Two services:

- **app**: Based on `mcr.microsoft.com/playwright/python:v1.49.0-noble`. Bundles Playwright + Chromium. Runs FastAPI via uvicorn. Mounts `./backend` as volume for development.
- **db**: PostgreSQL 16 (`postgres:16-alpine`). Persistent volume for data. Exposes port 5432.

No separate Playwright service — browser runs inside the app container.

### Dockerfile

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

---

## 4. Database Models

All models use UUID primary keys, async SQLAlchemy 2.0 with asyncpg driver.

### 4.1 User

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK, server_default=uuid4 |
| email | VARCHAR(255) | unique, indexed |
| password_hash | VARCHAR(255) | bcrypt |
| created_at | TIMESTAMP | server_default=now() |

### 4.2 Project

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| user_id | UUID | FK -> Users, indexed |
| name | VARCHAR(255) | |
| filters | JSONB | Stores ProjectFilters (see Section 6) |
| scrape_url | TEXT | Constructed URL from filters |
| is_active | BOOLEAN | default true |
| ai_scoring_enabled | BOOLEAN | default false |
| created_at | TIMESTAMP | server_default=now() |
| last_scraped_at | TIMESTAMP | nullable |

### 4.3 Listing

| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| project_id | UUID | FK -> Projects, indexed |
| external_id | VARCHAR(100) | From URL suffix `_7292256` |
| url | TEXT | Full listing URL |
| title | TEXT | |
| location | VARCHAR(255) | |
| region | VARCHAR(100) | |
| property_type | VARCHAR(50) | |
| transaction_type | VARCHAR(20) | |
| price | DECIMAL(12,2) | |
| price_per_m2 | DECIMAL(10,2) | nullable |
| size_m2 | DECIMAL(8,2) | nullable |
| rooms | VARCHAR(20) | |
| year_built | INTEGER | nullable |
| year_renovated | INTEGER | nullable |
| floor | VARCHAR(20) | nullable |
| land_size_m2 | DECIMAL(10,2) | nullable |
| energy_class | VARCHAR(10) | nullable |
| description | TEXT | nullable |
| images | JSONB | Array of image URLs, default [] |
| agency | VARCHAR(255) | nullable |
| basic_score | DECIMAL(5,2) | nullable (Phase 2) |
| ai_score | DECIMAL(5,2) | nullable (Phase 4) |
| ai_analysis | TEXT | nullable (Phase 4) |
| status | VARCHAR(20) | "active" / "sold" / "price_changed", default "active" |
| price_history | JSONB | `[{"price": 283000.00, "date": "2026-04-04"}]`, default [] |
| consecutive_misses | INTEGER | default 0, for sold detection |
| first_seen_at | TIMESTAMP | |
| last_seen_at | TIMESTAMP | |
| marked_sold_at | TIMESTAMP | nullable |
| created_at | TIMESTAMP | server_default=now() |

**Indexes:**
- `ix_listings_project_id` on project_id
- `uq_listings_project_external` UNIQUE on (project_id, external_id)
- `ix_listings_project_status` on (project_id, status)
- `ix_listings_external_id` on external_id

### 4.4 Alembic

Initial migration creates all three tables. `alembic/env.py` configured for async with asyncpg.

---

## 5. Configuration

### config.py

Uses `pydantic-settings` to load from `.env`:

```python
class Settings(BaseSettings):
    DATABASE_URL: str
    SCRAPER_HEADLESS: bool = True
    SCRAPER_MAX_DETAIL_PAGES_PER_RUN: int = 100
    SCRAPER_PAGE_DELAY_MIN: float = 2.0
    SCRAPER_PAGE_DELAY_MAX: float = 5.0
    SCRAPER_DETAIL_DELAY_MIN: float = 1.0
    SCRAPER_DETAIL_DELAY_MAX: float = 3.0
    SCRAPER_PAGE_TIMEOUT_MS: int = 30000
    SCRAPER_MAX_RETRIES: int = 3

    model_config = SettingsConfigDict(env_file=".env")
```

### .env.example

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/nepremicnine_tracker
SCRAPER_HEADLESS=true
SCRAPER_MAX_DETAIL_PAGES_PER_RUN=100
SCRAPER_PAGE_DELAY_MIN=2
SCRAPER_PAGE_DELAY_MAX=5
```

---

## 6. Filter Model & URL Builder

### 6.1 Filter Model

```python
class ProjectFilters(BaseModel):
    transaction: Literal["prodaja", "oddaja"]
    region: str           # URL slug from REGIONS
    sub_region: str | None = None  # URL slug from SUBREGIONS[region]
    property_type: str    # URL slug from PROPERTY_TYPES
    rooms: list[str] | None = None  # Only for stanovanje
    price_from: int | None = None
    price_to: int | None = None
    size_from: int | None = None
    size_to: int | None = None
    year_from: int | None = None
    year_to: int | None = None
```

### 6.2 URL Construction

Base pattern:
```
https://www.nepremicnine.net/oglasi-{transaction}/{region}/{sub_region?}/{property_type}/{rooms?}/{price_range?}/{size_range?}/{year_range?}/
```

Rules:
- `rooms` comma-joined: `2-sobno,3-sobno` — only valid when `property_type == "stanovanje"`
- `price_range`: `cena-od-{from}-do-{to}-eur`, `cena-od-{from}-eur`, `cena-do-{to}-eur`
- `size_range`: `velikost-od-{from}-do-{to}-m2` (same pattern)
- `year_range`: `letnik-od-{from}-do-{to}` (same pattern)
- Pagination: append `{page_number}/` to the URL (page 2 = `2/`, page 3 = `3/`, etc.)

### 6.3 Validation

- `region` must be a key in `REGIONS`
- `sub_region` (if set) must be a key in `SUBREGIONS[region]`
- `rooms` only allowed when `property_type == "stanovanje"`
- Each room value must be in `ROOM_TYPES`
- `price_from <= price_to`, `size_from <= size_to`, `year_from <= year_to` (when both set)
- `property_type` must be a key in `PROPERTY_TYPES`

---

## 7. Scraper Architecture

### 7.1 Browser Lifecycle (`browser.py`)

```python
async def create_browser_context(settings: Settings) -> tuple[Browser, BrowserContext]:
    """Launch Chromium and return a fresh browser context.
    
    IMPORTANT: The site requires a fresh browser context per navigation session.
    Reusing contexts causes dynamic elements (facets, filters) to not render.
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=settings.SCRAPER_HEADLESS)
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
    )
    return playwright, browser, context
```

Caller is responsible for closing browser after use.

### 7.2 List Parser (`list_parser.py`)

Parses search results pages. Input: Playwright `Page` after navigation. Output: list of `ListingCard` dataclass + total page count.

**Selectors** (based on site inspection):
- Card container: `.property-box`
- Title: `h2` inside card
- URL + external_id: `a[href*="_"]` — extract numeric suffix after `_`
- Price: `meta[itemprop="price"]` content attribute (numeric string like `"1180000.00"`)
- Size/year/floor: `ul[itemprop="disambiguatingDescription"] li` — parse icon-paired items
- Rooms: `span.tipi` text
- Transaction + property type: first `span.font-roboto` text ("Prodaja: Stanovanje, 3-sobno")
- Agency name: `meta[itemprop="name"]` inside `[itemprop="seller"]`
- Thumbnail: first `img[data-src]` in slider
- Page count: numbered `a` links matching `/{property_type}/{N}/` pattern — highest N = last page

**25 listings per page** (not 16 as originally assumed).

### 7.3 Detail Parser (`detail_parser.py`)

Parses individual listing pages. Input: Playwright `Page`. Output: `ListingDetail` dataclass.

Extracts data not available on the list card:
- Full description text
- All image URLs from the gallery (not just thumbnail)
- Energy class
- Land size (for houses)
- Year renovated (distinct from year built)
- Detailed location/neighborhood info

### 7.4 Scraper Orchestrator (`scraper.py`)

```python
async def scrape_project(filters: ProjectFilters, settings: Settings) -> list[ScrapedListing]:
    """Full scrape pipeline for a project's filters.
    
    1. Build URL from filters
    2. Launch fresh browser context
    3. Navigate to page 1:
       - Extract listing cards
       - Detect total page count
    4. For pages 2..N:
       - Random delay (SCRAPER_PAGE_DELAY_MIN to SCRAPER_PAGE_DELAY_MAX seconds)
       - Navigate, extract cards
    5. For each card (up to SCRAPER_MAX_DETAIL_PAGES_PER_RUN):
       - Random delay (SCRAPER_DETAIL_DELAY_MIN to SCRAPER_DETAIL_DELAY_MAX seconds)
       - Navigate to detail page
       - Merge detail data with card data
       - On failure after retries: keep card-level data (partial)
    6. Close browser
    7. Return list of ScrapedListing pydantic models
    """
```

### 7.5 Resilience

- **Retry per page**: max 3 attempts, exponential backoff (2s, 4s, 8s)
- **Partial data on detail failure**: if a detail page fails after retries, the listing is kept with card-level data only (description, extra images, energy class will be null)
- **Page timeout**: 30 seconds per navigation
- **Detail page cap**: `SCRAPER_MAX_DETAIL_PAGES_PER_RUN` (default 100)
- **All errors logged**, never crash the caller — return whatever was successfully scraped
- **Browser always closed** in a finally block

### 7.6 Rate Limiting & Politeness

- Random delay between list pages: 2-5 seconds (configurable)
- Random delay between detail pages: 1-3 seconds (configurable)
- Max 100 detail pages per run (configurable)
- Realistic user-agent and viewport
- No concurrent requests — fully sequential

---

## 8. Constants (`constants.py`)

### 8.1 Regions (13)

```python
REGIONS = {
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
```

### 8.2 Sub-regions (71 total)

```python
SUBREGIONS = {
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
```

### 8.3 Property Types

```python
PROPERTY_TYPES = {
    "stanovanje": "Stanovanje",
    "hisa": "Hiša",
    "vikend": "Vikend",
    "posest": "Posest",
    "poslovni-prostor": "Poslovni prostor",
    "garaza": "Garaža",
    "pocitniski-objekt": "Počitniški objekt",
}
```

### 8.4 Room Types (stanovanje only)

```python
ROOM_TYPES = [
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
```

### 8.5 Transaction Types

```python
TRANSACTION_TYPES = ["prodaja", "oddaja"]
```

---

## 9. Pydantic Schemas

### ScrapedListing

```python
class ScrapedListing(BaseModel):
    external_id: str
    url: str
    title: str
    location: str | None = None
    region: str | None = None
    property_type: str | None = None
    transaction_type: str | None = None
    price: Decimal | None = None
    price_per_m2: Decimal | None = None
    size_m2: Decimal | None = None
    rooms: str | None = None
    year_built: int | None = None
    year_renovated: int | None = None
    floor: str | None = None
    land_size_m2: Decimal | None = None
    energy_class: str | None = None
    description: str | None = None
    images: list[str] = []
    agency: str | None = None
```

Fields are nullable where detail page data might be unavailable (partial scrape on detail failure).

---

## 10. Testing Strategy

### 10.1 Unit Tests (no browser, no network)

**test_url_builder.py:**
- Basic URL: transaction + region + property type
- With sub-region
- With rooms (single, multiple, comma-joined)
- With price range (from only, to only, both)
- With size range
- With year range
- All filters combined
- Pagination URL generation (page 2, 3, etc.)
- Validation: invalid region, invalid room on non-stanovanje, price_from > price_to

**test_list_parser.py:**
- Parse cards from saved HTML fixture
- Extract external_id from URL
- Parse price from meta tag
- Parse size, year, floor from disambiguatingDescription
- Parse rooms from .tipi span
- Detect page count from pagination links
- Handle edge cases: missing price, missing year, unusual formats

**test_detail_parser.py:**
- Parse full description
- Extract all image URLs
- Parse energy class, land size, year renovated
- Handle missing optional fields

### 10.2 Integration Test (needs browser + network)

**test_scraper.py:**
- `@pytest.mark.integration` — skipped by default
- Scrapes Zasavska/stanovanje (small result set)
- Verifies returned ScrapedListing objects have valid data
- Checks that external_id, url, title, price are populated

### 10.3 Test Fixtures

Directory: `tests/fixtures/`
- `list_page.html` — saved search results page
- `detail_page.html` — saved listing detail page
- Captured during initial development, updated if site HTML changes

---

## 11. Dependencies (requirements.txt)

```
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.30.0
alembic>=1.14.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
playwright>=1.49.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

---

## 12. Corrections to Original Spec

Based on live site inspection (2026-04-04):

1. **Pagination** is path-based (`/stanovanje/2/`, `/stanovanje/3/`), not query-param `?s=16`. The `?s=` parameter controls **sorting** (by price, size, location, etc.), not pagination.
2. **25 listings per page**, not 16.
3. **Fresh browser context required** per navigation session. Reusing browser contexts causes dynamic elements (facets, filters) to not render correctly.
4. **Schema.org markup** is rich — price available as `<meta itemprop="price" content="1180000.00">`, making parsing more reliable than text scraping.
5. **Sub-regions** are exposed via `#facetUE` sidebar facets, labeled "Upravne enote" (administrative units).
6. **Room type slugs** on the site use no dots: `15-sobno` (not `1.5-sobno`), `25-sobno` (not `2.5-sobno`).

---

## 13. Out of Scope for Phase 1

- API endpoints (except health check)
- Authentication
- Scheduler / automated scraping
- Investment scoring (basic or AI)
- Frontend
- Price history tracking / sold detection logic (DB columns are created but logic is Phase 2)
- Croatia/other countries (`country` filter from original spec) — only Slovenia supported
