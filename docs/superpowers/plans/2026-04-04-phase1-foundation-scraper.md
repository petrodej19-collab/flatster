# Phase 1: Foundation + Scraper — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up the project infrastructure (Docker, DB, config) and build a working Playwright scraper that extracts apartment listings from nepremicnine.net.

**Architecture:** FastAPI backend with async SQLAlchemy + PostgreSQL, Playwright headless Chromium for scraping. Single-pass sequential scraper: list pages -> detail pages -> structured Pydantic models. Fresh browser context per scrape run.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async/asyncpg), Alembic, Playwright, Pydantic v2, pydantic-settings, PostgreSQL 16, Docker Compose, pytest

**Spec:** `docs/superpowers/specs/2026-04-04-phase1-foundation-scraper-design.md`

---

## File Map

| File | Responsibility |
|---|---|
| `Dockerfile` | App container based on Playwright Python image |
| `docker-compose.yml` | App + PostgreSQL services |
| `.env.example` | Template environment variables |
| `.gitignore` | Python/Node/Docker ignores |
| `backend/requirements.txt` | Python dependencies |
| `backend/app/__init__.py` | Package init |
| `backend/app/main.py` | FastAPI app with health check |
| `backend/app/config.py` | Settings via pydantic-settings |
| `backend/app/database.py` | Async SQLAlchemy engine + session |
| `backend/app/models/__init__.py` | Re-exports all models |
| `backend/app/models/base.py` | DeclarativeBase |
| `backend/app/models/user.py` | User ORM model |
| `backend/app/models/project.py` | Project ORM model |
| `backend/app/models/listing.py` | Listing ORM model |
| `backend/app/schemas/__init__.py` | Package init |
| `backend/app/schemas/scraper.py` | ScrapedListing + ProjectFilters Pydantic models |
| `backend/app/scraper/__init__.py` | Package init |
| `backend/app/scraper/constants.py` | Regions, sub-regions, property types, room types |
| `backend/app/scraper/url_builder.py` | `build_scrape_url()` + `build_paginated_url()` |
| `backend/app/scraper/browser.py` | Playwright browser lifecycle management |
| `backend/app/scraper/list_parser.py` | Parse listing cards from search results page |
| `backend/app/scraper/detail_parser.py` | Parse individual listing detail pages |
| `backend/app/scraper/scraper.py` | Orchestrator: paginate -> parse -> visit details |
| `backend/alembic.ini` | Alembic config |
| `backend/alembic/env.py` | Async migration environment |
| `backend/alembic/versions/001_initial_schema.py` | Initial migration (users, projects, listings) |
| `backend/tests/__init__.py` | Package init |
| `backend/tests/conftest.py` | Shared fixtures |
| `backend/tests/fixtures/list_page.html` | Saved search results HTML |
| `backend/tests/fixtures/detail_page.html` | Saved listing detail HTML |
| `backend/tests/test_url_builder.py` | URL builder tests |
| `backend/tests/test_list_parser.py` | List parser tests |
| `backend/tests/test_detail_parser.py` | Detail parser tests |
| `backend/tests/test_scraper.py` | Integration test (browser + network) |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `.gitignore`, `.env.example`, `Dockerfile`, `docker-compose.yml`, `backend/requirements.txt`, `backend/app/__init__.py`, `backend/app/main.py`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
dist/
build/
.eggs/
*.egg

# Virtual env
.venv/
venv/
env/

# Environment
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# Docker
docker-compose.override.yml

# Testing
.pytest_cache/
htmlcov/
.coverage

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 2: Create `.env.example`**

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/nepremicnine_tracker

# Scraper
SCRAPER_HEADLESS=true
SCRAPER_MAX_DETAIL_PAGES_PER_RUN=100
SCRAPER_PAGE_DELAY_MIN=2.0
SCRAPER_PAGE_DELAY_MAX=5.0
SCRAPER_DETAIL_DELAY_MIN=1.0
SCRAPER_DETAIL_DELAY_MAX=3.0
SCRAPER_PAGE_TIMEOUT_MS=30000
SCRAPER_MAX_RETRIES=3
```

- [ ] **Step 3: Create `backend/requirements.txt`**

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

- [ ] **Step 4: Create `Dockerfile`**

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.49.0-noble

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 5: Create `docker-compose.yml`**

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: nepremicnine_tracker
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

- [ ] **Step 6: Create `backend/app/__init__.py`** (empty file)

- [ ] **Step 7: Create `backend/app/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="NepremicnineTracker", version="0.1.0")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

- [ ] **Step 8: Copy `.env.example` to `.env` for local development**

Run: `cp .env.example .env`

- [ ] **Step 9: Verify Docker Compose starts**

Run: `docker compose up --build -d`

Expected: Both `app` and `db` services start. Health check at `http://localhost:8000/health` returns `{"status": "ok"}`.

Run: `curl http://localhost:8000/health`

Then stop: `docker compose down`

- [ ] **Step 10: Commit**

```bash
git add .gitignore .env.example Dockerfile docker-compose.yml backend/requirements.txt backend/app/__init__.py backend/app/main.py
git commit -m "feat: project scaffolding with Docker, FastAPI health check"
```

---

## Task 2: Configuration

**Files:**
- Create: `backend/app/config.py`

- [ ] **Step 1: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/nepremicnine_tracker"

    SCRAPER_HEADLESS: bool = True
    SCRAPER_MAX_DETAIL_PAGES_PER_RUN: int = 100
    SCRAPER_PAGE_DELAY_MIN: float = 2.0
    SCRAPER_PAGE_DELAY_MAX: float = 5.0
    SCRAPER_DETAIL_DELAY_MIN: float = 1.0
    SCRAPER_DETAIL_DELAY_MAX: float = 3.0
    SCRAPER_PAGE_TIMEOUT_MS: int = 30000
    SCRAPER_MAX_RETRIES: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/config.py
git commit -m "feat: add pydantic-settings configuration"
```

---

## Task 3: Database Setup + ORM Models

**Files:**
- Create: `backend/app/database.py`, `backend/app/models/__init__.py`, `backend/app/models/base.py`, `backend/app/models/user.py`, `backend/app/models/project.py`, `backend/app/models/listing.py`

- [ ] **Step 1: Create `backend/app/database.py`**

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with async_session() as session:
        yield session
```

- [ ] **Step 2: Create `backend/app/models/base.py`**

```python
import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


# Re-import datetime at module level for the mixin
from datetime import datetime  # noqa: E402
```

Wait — the import order is wrong. Let me fix that. The `datetime` import must come before the mixin that uses it.

- [ ] **Step 2 (corrected): Create `backend/app/models/base.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

- [ ] **Step 3: Create `backend/app/models/user.py`**

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
```

- [ ] **Step 4: Create `backend/app/models/project.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Project(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    filters: Mapped[dict] = mapped_column(JSONB, default=dict)
    scrape_url: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_scoring_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_scraped_at: Mapped[datetime | None] = mapped_column(default=None)
```

- [ ] **Step 5: Create `backend/app/models/listing.py`**

```python
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Listing(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("project_id", "external_id", name="uq_listings_project_external"),
        Index("ix_listings_project_status", "project_id", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True
    )
    external_id: Mapped[str] = mapped_column(String(100), index=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255), default=None)
    region: Mapped[str | None] = mapped_column(String(100), default=None)
    property_type: Mapped[str | None] = mapped_column(String(50), default=None)
    transaction_type: Mapped[str | None] = mapped_column(String(20), default=None)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    price_per_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), default=None)
    size_m2: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), default=None)
    rooms: Mapped[str | None] = mapped_column(String(20), default=None)
    year_built: Mapped[int | None] = mapped_column(Integer, default=None)
    year_renovated: Mapped[int | None] = mapped_column(Integer, default=None)
    floor: Mapped[str | None] = mapped_column(String(20), default=None)
    land_size_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), default=None)
    energy_class: Mapped[str | None] = mapped_column(String(10), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    images: Mapped[list] = mapped_column(JSONB, default=list)
    agency: Mapped[str | None] = mapped_column(String(255), default=None)
    basic_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    ai_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    ai_analysis: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")
    price_history: Mapped[list] = mapped_column(JSONB, default=list)
    consecutive_misses: Mapped[int] = mapped_column(Integer, default=0)
    first_seen_at: Mapped[datetime | None] = mapped_column(default=None)
    last_seen_at: Mapped[datetime | None] = mapped_column(default=None)
    marked_sold_at: Mapped[datetime | None] = mapped_column(default=None)
```

- [ ] **Step 6: Create `backend/app/models/__init__.py`**

```python
from app.models.base import Base
from app.models.listing import Listing
from app.models.project import Project
from app.models.user import User

__all__ = ["Base", "Listing", "Project", "User"]
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/database.py backend/app/models/
git commit -m "feat: add database setup and ORM models (users, projects, listings)"
```

---

## Task 4: Alembic Migrations

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/` (directory)

- [ ] **Step 1: Initialize Alembic**

Run from `backend/` directory:

```bash
cd backend && pip install alembic sqlalchemy asyncpg && alembic init alembic
```

This creates `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/`.

- [ ] **Step 2: Update `backend/alembic.ini`**

Set the `sqlalchemy.url` line to empty (we'll use env.py to read from config):

Find the line `sqlalchemy.url = driver://user:pass@localhost/dbname` and replace with:

```ini
sqlalchemy.url =
```

- [ ] **Step 3: Replace `backend/alembic/env.py` for async support**

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.DATABASE_URL)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Generate initial migration**

Make sure PostgreSQL is running (`docker compose up db -d`), then from `backend/`:

```bash
cd backend && alembic revision --autogenerate -m "initial schema: users, projects, listings"
```

Expected: Creates a migration file in `backend/alembic/versions/`.

- [ ] **Step 5: Run the migration**

```bash
cd backend && alembic upgrade head
```

Expected: Tables `users`, `projects`, `listings` created in the database.

- [ ] **Step 6: Verify tables exist**

```bash
docker compose exec db psql -U postgres -d nepremicnine_tracker -c "\dt"
```

Expected output should list `users`, `projects`, `listings`, and `alembic_version` tables.

- [ ] **Step 7: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git commit -m "feat: add Alembic migrations for initial schema"
```

---

## Task 5: Constants

**Files:**
- Create: `backend/app/scraper/__init__.py`, `backend/app/scraper/constants.py`

- [ ] **Step 1: Create `backend/app/scraper/__init__.py`** (empty file)

- [ ] **Step 2: Create `backend/app/scraper/constants.py`**

```python
REGIONS: dict[str, str] = {
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

SUBREGIONS: dict[str, dict[str, str]] = {
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

PROPERTY_TYPES: dict[str, str] = {
    "stanovanje": "Stanovanje",
    "hisa": "Hiša",
    "vikend": "Vikend",
    "posest": "Posest",
    "poslovni-prostor": "Poslovni prostor",
    "garaza": "Garaža",
    "pocitniski-objekt": "Počitniški objekt",
}

ROOM_TYPES: list[str] = [
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

TRANSACTION_TYPES: list[str] = ["prodaja", "oddaja"]

BASE_URL = "https://www.nepremicnine.net"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

LISTINGS_PER_PAGE = 25
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/scraper/
git commit -m "feat: add scraper constants (regions, sub-regions, property types)"
```

---

## Task 6: Pydantic Schemas

**Files:**
- Create: `backend/app/schemas/__init__.py`, `backend/app/schemas/scraper.py`

- [ ] **Step 1: Create `backend/app/schemas/__init__.py`** (empty file)

- [ ] **Step 2: Create `backend/app/schemas/scraper.py`**

```python
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator

from app.scraper.constants import PROPERTY_TYPES, REGIONS, ROOM_TYPES, SUBREGIONS


class ProjectFilters(BaseModel):
    transaction: Literal["prodaja", "oddaja"]
    region: str
    sub_region: str | None = None
    property_type: str
    rooms: list[str] | None = None
    price_from: int | None = None
    price_to: int | None = None
    size_from: int | None = None
    size_to: int | None = None
    year_from: int | None = None
    year_to: int | None = None

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        if v not in REGIONS:
            raise ValueError(f"Invalid region: {v}. Must be one of: {list(REGIONS.keys())}")
        return v

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v: str) -> str:
        if v not in PROPERTY_TYPES:
            raise ValueError(f"Invalid property_type: {v}. Must be one of: {list(PROPERTY_TYPES.keys())}")
        return v

    @field_validator("sub_region")
    @classmethod
    def validate_sub_region(cls, v: str | None, info) -> str | None:
        if v is None:
            return v
        region = info.data.get("region")
        if region and region in SUBREGIONS:
            if v not in SUBREGIONS[region]:
                valid = list(SUBREGIONS[region].keys())
                raise ValueError(f"Invalid sub_region: {v} for region {region}. Must be one of: {valid}")
        return v

    @field_validator("rooms")
    @classmethod
    def validate_rooms(cls, v: list[str] | None, info) -> list[str] | None:
        if v is None:
            return v
        property_type = info.data.get("property_type")
        if property_type and property_type != "stanovanje":
            raise ValueError("rooms filter is only valid for property_type 'stanovanje'")
        for room in v:
            if room not in ROOM_TYPES:
                raise ValueError(f"Invalid room type: {room}. Must be one of: {ROOM_TYPES}")
        return v

    @field_validator("price_to")
    @classmethod
    def validate_price_range(cls, v: int | None, info) -> int | None:
        if v is not None and info.data.get("price_from") is not None:
            if v < info.data["price_from"]:
                raise ValueError("price_to must be >= price_from")
        return v

    @field_validator("size_to")
    @classmethod
    def validate_size_range(cls, v: int | None, info) -> int | None:
        if v is not None and info.data.get("size_from") is not None:
            if v < info.data["size_from"]:
                raise ValueError("size_to must be >= size_from")
        return v

    @field_validator("year_to")
    @classmethod
    def validate_year_range(cls, v: int | None, info) -> int | None:
        if v is not None and info.data.get("year_from") is not None:
            if v < info.data["year_from"]:
                raise ValueError("year_to must be >= year_from")
        return v


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

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/
git commit -m "feat: add Pydantic schemas (ProjectFilters, ScrapedListing)"
```

---

## Task 7: URL Builder + Tests

**Files:**
- Create: `backend/app/scraper/url_builder.py`, `backend/tests/__init__.py`, `backend/tests/test_url_builder.py`

- [ ] **Step 1: Write the tests first — create `backend/tests/__init__.py`** (empty file)

- [ ] **Step 2: Create `backend/tests/test_url_builder.py`**

```python
import pytest

from app.schemas.scraper import ProjectFilters
from app.scraper.url_builder import build_scrape_url, build_paginated_url


class TestBuildScrapeUrl:
    def test_basic_url(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="ljubljana-mesto",
            property_type="stanovanje",
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/"

    def test_with_sub_region(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="ljubljana-mesto",
            sub_region="lj-center",
            property_type="stanovanje",
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/lj-center/stanovanje/"

    def test_with_single_room(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="gorenjska",
            property_type="stanovanje",
            rooms=["2-sobno"],
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/gorenjska/stanovanje/2-sobno/"

    def test_with_multiple_rooms(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="gorenjska",
            property_type="stanovanje",
            rooms=["2-sobno", "3-sobno"],
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/gorenjska/stanovanje/2-sobno,3-sobno/"

    def test_with_price_range_both(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="ljubljana-mesto",
            property_type="stanovanje",
            price_from=100000,
            price_to=200000,
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/cena-od-100000-do-200000-eur/"

    def test_with_price_from_only(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="ljubljana-mesto",
            property_type="stanovanje",
            price_from=200000,
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/cena-od-200000-eur/"

    def test_with_price_to_only(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="ljubljana-mesto",
            property_type="stanovanje",
            price_to=200000,
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/cena-do-200000-eur/"

    def test_with_size_range(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="podravska",
            property_type="stanovanje",
            size_from=50,
            size_to=100,
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/podravska/stanovanje/velikost-od-50-do-100-m2/"

    def test_with_year_range(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="podravska",
            property_type="stanovanje",
            year_from=2000,
            year_to=2020,
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/podravska/stanovanje/letnik-od-2000-do-2020/"

    def test_rent_transaction(self):
        filters = ProjectFilters(
            transaction="oddaja",
            region="ljubljana-mesto",
            property_type="stanovanje",
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-oddaja/ljubljana-mesto/stanovanje/"

    def test_house_property_type(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="gorenjska",
            property_type="hisa",
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/gorenjska/hisa/"

    def test_all_filters_combined(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="ljubljana-mesto",
            sub_region="lj-center",
            property_type="stanovanje",
            rooms=["2-sobno", "25-sobno"],
            price_from=150000,
            price_to=300000,
            size_from=40,
            size_to=80,
            year_from=1990,
            year_to=2020,
        )
        url = build_scrape_url(filters)
        assert url == (
            "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/lj-center/"
            "stanovanje/2-sobno,25-sobno/cena-od-150000-do-300000-eur/"
            "velikost-od-40-do-80-m2/letnik-od-1990-do-2020/"
        )


class TestBuildPaginatedUrl:
    def test_page_1_returns_base_url(self):
        base = "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/"
        assert build_paginated_url(base, 1) == base

    def test_page_2(self):
        base = "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/"
        assert build_paginated_url(base, 2) == base + "2/"

    def test_page_10(self):
        base = "https://www.nepremicnine.net/oglasi-prodaja/gorenjska/stanovanje/2-sobno/"
        assert build_paginated_url(base, 10) == base + "10/"


class TestProjectFiltersValidation:
    def test_invalid_region(self):
        with pytest.raises(ValueError, match="Invalid region"):
            ProjectFilters(
                transaction="prodaja",
                region="invalid",
                property_type="stanovanje",
            )

    def test_invalid_sub_region(self):
        with pytest.raises(ValueError, match="Invalid sub_region"):
            ProjectFilters(
                transaction="prodaja",
                region="gorenjska",
                sub_region="invalid",
                property_type="stanovanje",
            )

    def test_rooms_on_non_stanovanje(self):
        with pytest.raises(ValueError, match="only valid for"):
            ProjectFilters(
                transaction="prodaja",
                region="gorenjska",
                property_type="hisa",
                rooms=["2-sobno"],
            )

    def test_invalid_room_type(self):
        with pytest.raises(ValueError, match="Invalid room type"):
            ProjectFilters(
                transaction="prodaja",
                region="gorenjska",
                property_type="stanovanje",
                rooms=["invalid"],
            )

    def test_price_from_greater_than_to(self):
        with pytest.raises(ValueError, match="price_to must be >= price_from"):
            ProjectFilters(
                transaction="prodaja",
                region="gorenjska",
                property_type="stanovanje",
                price_from=200000,
                price_to=100000,
            )

    def test_size_from_greater_than_to(self):
        with pytest.raises(ValueError, match="size_to must be >= size_from"):
            ProjectFilters(
                transaction="prodaja",
                region="gorenjska",
                property_type="stanovanje",
                size_from=100,
                size_to=50,
            )

    def test_year_from_greater_than_to(self):
        with pytest.raises(ValueError, match="year_to must be >= year_from"):
            ProjectFilters(
                transaction="prodaja",
                region="gorenjska",
                property_type="stanovanje",
                year_from=2020,
                year_to=2000,
            )
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_url_builder.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'app.scraper.url_builder'`

- [ ] **Step 4: Create `backend/app/scraper/url_builder.py`**

```python
from app.schemas.scraper import ProjectFilters
from app.scraper.constants import BASE_URL


def build_scrape_url(filters: ProjectFilters) -> str:
    """Build a nepremicnine.net search URL from project filters."""
    segments = [f"oglasi-{filters.transaction}", filters.region]

    if filters.sub_region:
        segments.append(filters.sub_region)

    segments.append(filters.property_type)

    if filters.rooms:
        segments.append(",".join(filters.rooms))

    price_seg = _build_range_segment(
        filters.price_from, filters.price_to, prefix="cena", suffix="eur"
    )
    if price_seg:
        segments.append(price_seg)

    size_seg = _build_range_segment(
        filters.size_from, filters.size_to, prefix="velikost", suffix="m2"
    )
    if size_seg:
        segments.append(size_seg)

    year_seg = _build_range_segment(
        filters.year_from, filters.year_to, prefix="letnik", suffix=None
    )
    if year_seg:
        segments.append(year_seg)

    return BASE_URL + "/" + "/".join(segments) + "/"


def build_paginated_url(base_url: str, page: int) -> str:
    """Append page number to a base search URL. Page 1 returns the base URL unchanged."""
    if page <= 1:
        return base_url
    return base_url + f"{page}/"


def _build_range_segment(
    from_val: int | None, to_val: int | None, prefix: str, suffix: str | None
) -> str | None:
    """Build a range URL segment like 'cena-od-100000-do-200000-eur'."""
    if from_val is None and to_val is None:
        return None

    parts = [prefix]
    if from_val is not None and to_val is not None:
        parts.append(f"od-{from_val}-do-{to_val}")
    elif from_val is not None:
        parts.append(f"od-{from_val}")
    else:
        parts.append(f"do-{to_val}")

    segment = "-".join(parts)
    if suffix:
        segment += f"-{suffix}"
    return segment
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_url_builder.py -v`

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/scraper/url_builder.py backend/tests/
git commit -m "feat: add URL builder with full filter support and tests"
```

---

## Task 8: Capture Test Fixtures

**Files:**
- Create: `backend/tests/fixtures/list_page.html`, `backend/tests/fixtures/detail_page.html`, `backend/tests/conftest.py`

This task captures real HTML from the site to use as offline test fixtures for parser unit tests. Run these commands locally (not in Docker) since Playwright is installed on the host.

- [ ] **Step 1: Create fixture capture script and run it**

Run from project root:

```bash
mkdir -p backend/tests/fixtures
python3 << 'PYEOF'
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    # Capture list page
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    page.goto('https://www.nepremicnine.net/oglasi-prodaja/zasavska/stanovanje/', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(3000)
    with open('backend/tests/fixtures/list_page.html', 'w') as f:
        f.write(page.content())
    print('Saved list_page.html')
    
    # Get first listing URL for detail page
    listing_url = page.evaluate("""() => {
        const link = document.querySelector('.property-box a[href*="_"]');
        return link ? link.getAttribute('href') : null;
    }""")
    browser.close()
    
    if listing_url:
        time.sleep(2)
        if not listing_url.startswith('http'):
            listing_url = 'https://www.nepremicnine.net' + listing_url
        
        # Capture detail page (fresh browser)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        page.goto(listing_url, wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(3000)
        with open('backend/tests/fixtures/detail_page.html', 'w') as f:
            f.write(page.content())
        print(f'Saved detail_page.html from {listing_url}')
        browser.close()
PYEOF
```

Expected: Two HTML files saved to `backend/tests/fixtures/`.

- [ ] **Step 2: Create `backend/tests/conftest.py`**

```python
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def list_page_html() -> str:
    return (FIXTURES_DIR / "list_page.html").read_text()


@pytest.fixture
def detail_page_html() -> str:
    return (FIXTURES_DIR / "detail_page.html").read_text()
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/conftest.py backend/tests/fixtures/
git commit -m "feat: add HTML test fixtures for parser unit tests"
```

---

## Task 9: List Parser + Tests

**Files:**
- Create: `backend/app/scraper/list_parser.py`, `backend/tests/test_list_parser.py`

- [ ] **Step 1: Create `backend/tests/test_list_parser.py`**

```python
import re
from decimal import Decimal

from app.scraper.list_parser import ListingCard, parse_list_page


class TestParseListPage:
    def test_returns_cards_and_page_count(self, list_page_html: str):
        cards, total_pages = parse_list_page(list_page_html)
        assert isinstance(cards, list)
        assert len(cards) > 0
        assert total_pages >= 1

    def test_card_has_required_fields(self, list_page_html: str):
        cards, _ = parse_list_page(list_page_html)
        card = cards[0]
        assert isinstance(card, ListingCard)
        assert card.external_id
        assert card.url
        assert card.title

    def test_external_id_is_numeric(self, list_page_html: str):
        cards, _ = parse_list_page(list_page_html)
        for card in cards:
            assert re.match(r"^\d+$", card.external_id), f"external_id should be numeric, got: {card.external_id}"

    def test_price_parsed_as_decimal(self, list_page_html: str):
        cards, _ = parse_list_page(list_page_html)
        cards_with_price = [c for c in cards if c.price is not None]
        assert len(cards_with_price) > 0, "At least one card should have a price"
        for card in cards_with_price:
            assert isinstance(card.price, Decimal)
            assert card.price > 0

    def test_url_is_absolute(self, list_page_html: str):
        cards, _ = parse_list_page(list_page_html)
        for card in cards:
            assert card.url.startswith("https://"), f"URL should be absolute, got: {card.url}"

    def test_thumbnail_url_when_present(self, list_page_html: str):
        cards, _ = parse_list_page(list_page_html)
        cards_with_thumb = [c for c in cards if c.thumbnail_url]
        # Most cards should have thumbnails
        assert len(cards_with_thumb) > 0
        for card in cards_with_thumb:
            assert "nepremicnine.net" in card.thumbnail_url
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_list_parser.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'app.scraper.list_parser'`

- [ ] **Step 3: Create `backend/app/scraper/list_parser.py`**

```python
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from app.scraper.constants import BASE_URL


@dataclass
class ListingCard:
    external_id: str
    url: str
    title: str
    price: Decimal | None = None
    size_m2: Decimal | None = None
    rooms: str | None = None
    year_built: int | None = None
    floor: str | None = None
    property_type: str | None = None
    transaction_type: str | None = None
    agency: str | None = None
    thumbnail_url: str | None = None


def parse_list_page(html: str) -> tuple[list[ListingCard], int]:
    """Parse listing cards and total page count from a search results HTML page.

    Returns (list of ListingCard, total_pages).
    """
    cards = _parse_cards(html)
    total_pages = _parse_total_pages(html)
    return cards, total_pages


def _parse_cards(html: str) -> list[ListingCard]:
    cards: list[ListingCard] = []

    # Split by property-box divs. Each card starts with class="property-box
    # We use a regex to find each card's HTML block.
    card_pattern = re.compile(
        r'<div\s+class="property-box[^"]*"[^>]*itemscope[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</div>',
        re.DOTALL,
    )
    # A simpler approach: find all blocks between property-box markers
    # Split on the property-box opening tag
    parts = re.split(r'<div\s+class="property-box\s', html)

    for part in parts[1:]:  # skip everything before first card
        card = _parse_single_card(part)
        if card:
            cards.append(card)

    return cards


def _parse_single_card(card_html: str) -> ListingCard | None:
    # External ID + URL: look for href with _DIGITS/
    url_match = re.search(
        r'href="(https://www\.nepremicnine\.net/[^"]*_(\d+)/)"', card_html
    )
    if not url_match:
        # Try relative URL
        url_match = re.search(r'href="(/[^"]*_(\d+)/)"', card_html)
        if not url_match:
            return None

    raw_url = url_match.group(1)
    url = raw_url if raw_url.startswith("http") else BASE_URL + raw_url
    external_id = url_match.group(2)

    # Title: first <h2> content
    title_match = re.search(r"<h2[^>]*>(.*?)</h2>", card_html, re.DOTALL)
    title = _clean_text(title_match.group(1)) if title_match else ""

    # Price: meta itemprop="price" content="1180000.00"
    price = None
    price_match = re.search(r'itemprop="price"\s+content="([^"]+)"', card_html)
    if price_match:
        try:
            price = Decimal(price_match.group(1))
        except InvalidOperation:
            pass

    # Size: from disambiguatingDescription list items — look for "m2" or "m<sup>2</sup>"
    size_m2 = None
    size_match = re.search(r"([\d.,]+)\s*m(?:<sup>)?2", card_html)
    if size_match:
        try:
            size_m2 = Decimal(size_match.group(1).replace(",", "."))
        except InvalidOperation:
            pass

    # Rooms: span.tipi content
    rooms = None
    rooms_match = re.search(r'class="tipi"[^>]*>(.*?)</span>', card_html, re.DOTALL)
    if rooms_match:
        rooms = _clean_text(rooms_match.group(1))

    # Year built: from disambiguatingDescription — 4-digit number near year icon
    year_built = None
    # The year appears in a <li> with a year icon, containing just a 4-digit number
    year_match = re.search(
        r'<li><img[^>]*leto\.svg[^>]*>(\d{4})</li>', card_html
    )
    if year_match:
        year_built = int(year_match.group(1))

    # Floor: from disambiguatingDescription — pattern like "3/5" near nadstropje icon
    floor = None
    floor_match = re.search(
        r'<li><img[^>]*nadstropje\.svg[^>]*>([\d/]+)', card_html
    )
    if floor_match:
        floor = floor_match.group(1)

    # Transaction + property type: "Prodaja: Stanovanje, 3-sobno"
    property_type = None
    transaction_type = None
    type_match = re.search(
        r'class="font-roboto"[^>]*>\s*(Prodaja|Oddaja|Najem|Nakup):\s*(\w+)',
        card_html,
        re.DOTALL,
    )
    if type_match:
        trans_map = {"Prodaja": "prodaja", "Oddaja": "oddaja", "Najem": "oddaja", "Nakup": "prodaja"}
        transaction_type = trans_map.get(type_match.group(1), type_match.group(1).lower())
        prop_map = {"Stanovanje": "stanovanje", "Hiša": "hisa", "Posest": "posest"}
        property_type = prop_map.get(type_match.group(2), type_match.group(2).lower())

    # Agency: meta itemprop="name" inside seller section
    agency = None
    agency_match = re.search(
        r'itemprop="seller".*?itemprop="name"\s+content="([^"]+)"',
        card_html,
        re.DOTALL,
    )
    if agency_match:
        agency = _clean_text(agency_match.group(1))

    # Thumbnail: first img with data-src containing slonep_oglasi
    thumbnail_url = None
    thumb_match = re.search(r'data-src="(https://img\.nepremicnine\.net/slonep_oglasi[^"]+)"', card_html)
    if thumb_match:
        thumbnail_url = thumb_match.group(1)

    return ListingCard(
        external_id=external_id,
        url=url,
        title=title,
        price=price,
        size_m2=size_m2,
        rooms=rooms,
        year_built=year_built,
        floor=floor,
        property_type=property_type,
        transaction_type=transaction_type,
        agency=agency,
        thumbnail_url=thumbnail_url,
    )


def _parse_total_pages(html: str) -> int:
    """Detect total page count from pagination links.

    Pagination links look like: href="/oglasi-prodaja/.../stanovanje/2/"
    where the number is the page. Find the highest page number.
    """
    # Match page number links: /{digits}/" where digits are the page number
    # These appear as numbered links in the pagination section
    page_matches = re.findall(r'href="[^"]+/(\d+)/"[^>]*>\s*\1\s*<', html)
    if not page_matches:
        return 1
    return max(int(p) for p in page_matches)


def _clean_text(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_list_parser.py -v`

Expected: All tests PASS. If any tests fail due to fixture HTML structure differences, adjust the parser regexes to match the actual HTML patterns in the fixture.

- [ ] **Step 5: Commit**

```bash
git add backend/app/scraper/list_parser.py backend/tests/test_list_parser.py
git commit -m "feat: add list page parser with tests"
```

---

## Task 10: Detail Parser + Tests

**Files:**
- Create: `backend/app/scraper/detail_parser.py`, `backend/tests/test_detail_parser.py`

- [ ] **Step 1: Create `backend/tests/test_detail_parser.py`**

```python
from app.scraper.detail_parser import ListingDetail, parse_detail_page


class TestParseDetailPage:
    def test_returns_listing_detail(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert isinstance(detail, ListingDetail)

    def test_has_description(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        # Description may or may not be present depending on the fixture
        # but the field should exist
        assert hasattr(detail, "description")

    def test_has_images(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert isinstance(detail.images, list)
        # Most listings have at least one image
        if detail.images:
            assert all("nepremicnine.net" in img for img in detail.images)

    def test_images_are_deduplicated(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert len(detail.images) == len(set(detail.images))

    def test_size_parsed(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        # size_m2 should be set from the attributes
        if detail.size_m2 is not None:
            assert detail.size_m2 > 0

    def test_year_fields(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        if detail.year_built is not None:
            assert 1800 < detail.year_built < 2100
        if detail.year_renovated is not None:
            assert 1800 < detail.year_renovated < 2100

    def test_floor_parsed(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        # floor may or may not be present
        assert hasattr(detail, "floor")

    def test_title_parsed(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        if detail.title:
            assert len(detail.title) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_detail_parser.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'app.scraper.detail_parser'`

- [ ] **Step 3: Create `backend/app/scraper/detail_parser.py`**

```python
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation


@dataclass
class ListingDetail:
    title: str | None = None
    description: str | None = None
    images: list[str] = field(default_factory=list)
    size_m2: Decimal | None = None
    floor: str | None = None
    year_built: int | None = None
    year_renovated: int | None = None
    energy_class: str | None = None
    land_size_m2: Decimal | None = None
    location: str | None = None
    num_bedrooms: int | None = None
    num_bathrooms: int | None = None


def parse_detail_page(html: str) -> ListingDetail:
    """Parse a listing detail page HTML and extract all available fields."""
    return ListingDetail(
        title=_parse_title(html),
        description=_parse_description(html),
        images=_parse_images(html),
        size_m2=_parse_size(html),
        floor=_parse_floor(html),
        year_built=_parse_year_built(html),
        year_renovated=_parse_year_renovated(html),
        energy_class=_parse_energy_class(html),
        land_size_m2=_parse_land_size(html),
        location=_parse_location(html),
        num_bedrooms=_parse_int_attribute(html, r"Št\.\s*spalnic:\s*(\d+)"),
        num_bathrooms=_parse_int_attribute(html, r"Št\.\s*kopalnic:\s*(\d+)"),
    )


def _parse_title(html: str) -> str | None:
    """Parse title from h1 tag. Format: 'BRDCE, 62.52 m2 - prodaja, stanovanje, 3-sobno'"""
    match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
    if match:
        return _clean_text(match.group(1))
    return None


def _parse_description(html: str) -> str | None:
    """Parse description from the #desc tab or the 'Dodaten opis' section."""
    # Try #desc tab content first
    match = re.search(
        r'id="desc"[^>]*>(.*?)</div>\s*(?:<div\s+class="tab-pane|$)',
        html,
        re.DOTALL,
    )
    if match:
        text = _clean_text(match.group(1))
        # Remove the "Dodaten opis nepremičnine" heading if present
        text = re.sub(r"^Dodaten opis nepremičnine\s*", "", text)
        if text:
            return text

    # Fallback: look for text after "Dodaten opis" heading
    match = re.search(
        r"Dodaten opis nepremičnine\s*</h4>\s*(.*?)(?:<h[34]|</div>\s*</div>)",
        html,
        re.DOTALL,
    )
    if match:
        text = _clean_text(match.group(1))
        if text:
            return text

    return None


def _parse_images(html: str) -> list[str]:
    """Extract all unique listing image URLs."""
    # Match img tags with data-src or src pointing to slonep_oglasi
    pattern = r'(?:data-src|src)="(https://img\.nepremicnine\.net/slonep_oglasi2?/[^"]+)"'
    urls = re.findall(pattern, html)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def _parse_size(html: str) -> Decimal | None:
    """Parse size from attributes: 'Velikost: 62,52 m2'"""
    match = re.search(r"Velikost:\s*([\d.,]+)\s*m", html)
    if match:
        try:
            return Decimal(match.group(1).replace(",", "."))
        except InvalidOperation:
            pass
    return None


def _parse_floor(html: str) -> str | None:
    """Parse floor from attributes: 'Nadstropje: 2/2' or 'pritličje'"""
    match = re.search(r"Nadstropje:\s*([\d/]+)", html)
    if match:
        return match.group(1)
    if re.search(r"pritličje", html, re.IGNORECASE):
        return "pritličje"
    return None


def _parse_year_built(html: str) -> int | None:
    """Parse year built from page text: 'zgrajeno l. 1997' or 'Leto izgradnje: 1997'"""
    patterns = [
        r"zgrajeno\s+l\.\s*(\d{4})",
        r"Leto izgradnje[:\s]*(\d{4})",
        r"začetek gradnje l\.\s*(\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _parse_year_renovated(html: str) -> int | None:
    """Parse year renovated: 'adaptirano l. 2020' or 'prenovljeno l. 2019'"""
    patterns = [
        r"adaptirano\s+l\.\s*(\d{4})",
        r"prenovljeno\s+l\.\s*(\d{4})",
        r"renovirano\s+l\.\s*(\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _parse_energy_class(html: str) -> str | None:
    """Parse energy class: 'energijski razred: B2'"""
    match = re.search(r"energijski razred[:\s]*([A-G]\d?)", html, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _parse_land_size(html: str) -> Decimal | None:
    """Parse land size: 'Zemljišče: 500,00 m2'"""
    match = re.search(r"Zemljišče:\s*([\d.,]+)\s*m", html)
    if match:
        try:
            val = Decimal(match.group(1).replace(",", "."))
            if val > 0:
                return val
        except InvalidOperation:
            pass
    return None


def _parse_location(html: str) -> str | None:
    """Parse location from the h1 title — first part before the comma."""
    match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.DOTALL)
    if match:
        title = _clean_text(match.group(1))
        # Title format: "LOCATION, size m2 - transaction, type, rooms"
        parts = title.split(",")
        if parts:
            return parts[0].strip()
    return None


def _parse_int_attribute(html: str, pattern: str) -> int | None:
    """Parse an integer from an attribute pattern."""
    match = re.search(pattern, html)
    if match:
        return int(match.group(1))
    return None


def _clean_text(text: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&quot;", '"', text)
    text = re.sub(r"&#\d+;", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_detail_parser.py -v`

Expected: All tests PASS. If any fail due to fixture HTML specifics, adjust parser regexes.

- [ ] **Step 5: Commit**

```bash
git add backend/app/scraper/detail_parser.py backend/tests/test_detail_parser.py
git commit -m "feat: add detail page parser with tests"
```

---

## Task 11: Browser Lifecycle

**Files:**
- Create: `backend/app/scraper/browser.py`

- [ ] **Step 1: Create `backend/app/scraper/browser.py`**

```python
import logging
from dataclasses import dataclass

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from app.config import Settings
from app.scraper.constants import USER_AGENT

logger = logging.getLogger(__name__)


@dataclass
class BrowserSession:
    """Holds Playwright resources for cleanup."""

    playwright: Playwright
    browser: Browser
    context: BrowserContext


async def create_browser_session(settings: Settings) -> BrowserSession:
    """Launch headless Chromium and return a fresh browser session.

    IMPORTANT: nepremicnine.net requires a fresh browser context per session.
    Reusing contexts causes dynamic page elements to not render.

    The caller MUST call close_browser_session() when done.
    """
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=settings.SCRAPER_HEADLESS)
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1920, "height": 1080},
    )
    logger.info("Browser session created (headless=%s)", settings.SCRAPER_HEADLESS)
    return BrowserSession(playwright=pw, browser=browser, context=context)


async def close_browser_session(session: BrowserSession) -> None:
    """Close all Playwright resources."""
    try:
        await session.context.close()
        await session.browser.close()
        await session.playwright.stop()
        logger.info("Browser session closed")
    except Exception:
        logger.exception("Error closing browser session")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/scraper/browser.py
git commit -m "feat: add Playwright browser lifecycle management"
```

---

## Task 12: Scraper Orchestrator

**Files:**
- Create: `backend/app/scraper/scraper.py`

- [ ] **Step 1: Create `backend/app/scraper/scraper.py`**

```python
import asyncio
import logging
import random
from decimal import Decimal

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from app.config import Settings
from app.schemas.scraper import ProjectFilters, ScrapedListing
from app.scraper.browser import BrowserSession, close_browser_session, create_browser_session
from app.scraper.detail_parser import ListingDetail, parse_detail_page
from app.scraper.list_parser import ListingCard, parse_list_page
from app.scraper.url_builder import build_paginated_url, build_scrape_url

logger = logging.getLogger(__name__)


async def scrape_project(
    filters: ProjectFilters, settings: Settings
) -> list[ScrapedListing]:
    """Full scrape pipeline for a project's filters.

    1. Build URL from filters
    2. Launch fresh browser context
    3. Paginate through list pages, extracting cards
    4. Visit detail pages for each card (up to max limit)
    5. Merge card + detail data into ScrapedListing models
    6. Close browser
    """
    base_url = build_scrape_url(filters)
    logger.info("Starting scrape for URL: %s", base_url)

    session = await create_browser_session(settings)
    try:
        # Phase 1: Collect all cards from list pages
        all_cards = await _scrape_list_pages(session, base_url, settings)
        logger.info("Collected %d listing cards", len(all_cards))

        # Phase 2: Visit detail pages
        listings = await _scrape_detail_pages(session, all_cards, settings)
        logger.info("Completed scrape: %d listings with details", len(listings))

        return listings
    finally:
        await close_browser_session(session)


async def _scrape_list_pages(
    session: BrowserSession, base_url: str, settings: Settings
) -> list[ListingCard]:
    """Scrape all list pages and return all listing cards."""
    page = await session.context.new_page()
    all_cards: list[ListingCard] = []

    try:
        # Page 1
        html = await _navigate_with_retry(page, base_url, settings)
        if html is None:
            return []

        cards, total_pages = parse_list_page(html)
        all_cards.extend(cards)
        logger.info("Page 1/%d: %d cards", total_pages, len(cards))

        # Remaining pages
        for page_num in range(2, total_pages + 1):
            delay = random.uniform(settings.SCRAPER_PAGE_DELAY_MIN, settings.SCRAPER_PAGE_DELAY_MAX)
            await asyncio.sleep(delay)

            page_url = build_paginated_url(base_url, page_num)
            html = await _navigate_with_retry(page, page_url, settings)
            if html is None:
                logger.warning("Failed to load page %d, stopping pagination", page_num)
                break

            cards, _ = parse_list_page(html)
            all_cards.extend(cards)
            logger.info("Page %d/%d: %d cards", page_num, total_pages, len(cards))

    finally:
        await page.close()

    return all_cards


async def _scrape_detail_pages(
    session: BrowserSession,
    cards: list[ListingCard],
    settings: Settings,
) -> list[ScrapedListing]:
    """Visit detail pages and merge data with card data."""
    page = await session.context.new_page()
    listings: list[ScrapedListing] = []
    max_details = settings.SCRAPER_MAX_DETAIL_PAGES_PER_RUN

    try:
        for i, card in enumerate(cards):
            if i >= max_details:
                logger.info("Reached detail page limit (%d), remaining cards will have card-level data only", max_details)
                # Add remaining cards without detail data
                for remaining_card in cards[i:]:
                    listings.append(_card_to_listing(remaining_card))
                break

            if i > 0:
                delay = random.uniform(settings.SCRAPER_DETAIL_DELAY_MIN, settings.SCRAPER_DETAIL_DELAY_MAX)
                await asyncio.sleep(delay)

            html = await _navigate_with_retry(page, card.url, settings)
            if html is None:
                logger.warning("Failed to load detail page for %s, using card data only", card.external_id)
                listings.append(_card_to_listing(card))
                continue

            detail = parse_detail_page(html)
            listings.append(_merge_card_and_detail(card, detail))

            if (i + 1) % 10 == 0:
                logger.info("Detail pages: %d/%d completed", i + 1, min(len(cards), max_details))
    finally:
        await page.close()

    return listings


async def _navigate_with_retry(
    page: Page, url: str, settings: Settings
) -> str | None:
    """Navigate to URL with retry logic. Returns page HTML or None on failure."""
    for attempt in range(settings.SCRAPER_MAX_RETRIES):
        try:
            await page.goto(url, wait_until="networkidle", timeout=settings.SCRAPER_PAGE_TIMEOUT_MS)
            await page.wait_for_timeout(1000)  # Brief wait for dynamic content
            return await page.content()
        except PlaywrightTimeout:
            logger.warning("Timeout loading %s (attempt %d/%d)", url, attempt + 1, settings.SCRAPER_MAX_RETRIES)
        except Exception:
            logger.exception("Error loading %s (attempt %d/%d)", url, attempt + 1, settings.SCRAPER_MAX_RETRIES)

        if attempt < settings.SCRAPER_MAX_RETRIES - 1:
            backoff = 2 ** (attempt + 1)
            await asyncio.sleep(backoff)

    return None


def _card_to_listing(card: ListingCard) -> ScrapedListing:
    """Convert a ListingCard (list page data only) to a ScrapedListing."""
    price_per_m2 = None
    if card.price and card.size_m2 and card.size_m2 > 0:
        price_per_m2 = (card.price / card.size_m2).quantize(Decimal("0.01"))

    return ScrapedListing(
        external_id=card.external_id,
        url=card.url,
        title=card.title,
        price=card.price,
        price_per_m2=price_per_m2,
        size_m2=card.size_m2,
        rooms=card.rooms,
        year_built=card.year_built,
        floor=card.floor,
        property_type=card.property_type,
        transaction_type=card.transaction_type,
        agency=card.agency,
        images=[card.thumbnail_url] if card.thumbnail_url else [],
    )


def _merge_card_and_detail(card: ListingCard, detail: "ListingDetail") -> ScrapedListing:
    """Merge card-level data with detail page data. Detail data takes precedence where available."""
    size = detail.size_m2 if detail.size_m2 is not None else card.size_m2
    price_per_m2 = None
    if card.price and size and size > 0:
        price_per_m2 = (card.price / size).quantize(Decimal("0.01"))

    return ScrapedListing(
        external_id=card.external_id,
        url=card.url,
        title=detail.title or card.title,
        location=detail.location,
        property_type=card.property_type,
        transaction_type=card.transaction_type,
        price=card.price,
        price_per_m2=price_per_m2,
        size_m2=size,
        rooms=card.rooms,
        year_built=detail.year_built or card.year_built,
        year_renovated=detail.year_renovated,
        floor=detail.floor or card.floor,
        land_size_m2=detail.land_size_m2,
        energy_class=detail.energy_class,
        description=detail.description,
        images=detail.images if detail.images else ([card.thumbnail_url] if card.thumbnail_url else []),
        agency=card.agency,
    )
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/scraper/scraper.py
git commit -m "feat: add scraper orchestrator with pagination, detail pages, retry logic"
```

---

## Task 13: Integration Test

**Files:**
- Create: `backend/tests/test_scraper.py`

- [ ] **Step 1: Create `backend/tests/test_scraper.py`**

```python
import asyncio
import re

import pytest

from app.config import Settings
from app.schemas.scraper import ProjectFilters, ScrapedListing
from app.scraper.scraper import scrape_project

pytestmark = pytest.mark.integration


@pytest.fixture
def integration_settings() -> Settings:
    """Settings for integration testing — limit detail pages to keep tests fast."""
    return Settings(
        DATABASE_URL="postgresql+asyncpg://unused:unused@localhost/unused",
        SCRAPER_HEADLESS=True,
        SCRAPER_MAX_DETAIL_PAGES_PER_RUN=3,
        SCRAPER_PAGE_DELAY_MIN=2.0,
        SCRAPER_PAGE_DELAY_MAX=3.0,
        SCRAPER_DETAIL_DELAY_MIN=1.0,
        SCRAPER_DETAIL_DELAY_MAX=2.0,
        SCRAPER_PAGE_TIMEOUT_MS=30000,
        SCRAPER_MAX_RETRIES=2,
    )


@pytest.mark.asyncio
async def test_scrape_returns_listings(integration_settings: Settings):
    """End-to-end test: scrape a small region and verify structured output."""
    filters = ProjectFilters(
        transaction="prodaja",
        region="zasavska",
        property_type="stanovanje",
    )

    listings = await scrape_project(filters, integration_settings)

    assert len(listings) > 0, "Should find at least one listing in Zasavska"
    for listing in listings:
        assert isinstance(listing, ScrapedListing)
        assert listing.external_id
        assert re.match(r"^\d+$", listing.external_id)
        assert listing.url.startswith("https://")
        assert listing.title


@pytest.mark.asyncio
async def test_scraped_listing_has_price(integration_settings: Settings):
    """Most listings should have a price."""
    filters = ProjectFilters(
        transaction="prodaja",
        region="zasavska",
        property_type="stanovanje",
    )

    listings = await scrape_project(filters, integration_settings)
    listings_with_price = [l for l in listings if l.price is not None]
    assert len(listings_with_price) > 0, "At least one listing should have a price"
    for listing in listings_with_price:
        assert listing.price > 0


@pytest.mark.asyncio
async def test_detail_pages_have_extra_data(integration_settings: Settings):
    """Listings that had detail pages scraped should have images or description."""
    filters = ProjectFilters(
        transaction="prodaja",
        region="zasavska",
        property_type="stanovanje",
    )

    listings = await scrape_project(filters, integration_settings)
    # First 3 listings should have detail page data (max_detail_pages=3)
    detailed = listings[:3]
    has_extra = any(l.description or len(l.images) > 1 for l in detailed)
    assert has_extra, "At least one detailed listing should have description or multiple images"
```

- [ ] **Step 2: Configure pytest to skip integration tests by default**

Create `backend/pytest.ini`:

```ini
[pytest]
markers =
    integration: marks tests that require browser + network (deselect with '-m "not integration"')
addopts = -m "not integration"
pythonpath = .
```

- [ ] **Step 3: Run unit tests (should pass, integration tests skipped)**

Run: `cd backend && python -m pytest -v`

Expected: All unit tests pass, integration tests are skipped.

- [ ] **Step 4: Run integration test explicitly**

Run: `cd backend && python -m pytest tests/test_scraper.py -m integration -v`

Expected: Tests PASS (takes ~30-60 seconds due to browser + network + delays).

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_scraper.py backend/pytest.ini
git commit -m "feat: add integration test for end-to-end scraper pipeline"
```

---

## Task 14: Final Verification

- [ ] **Step 1: Run all unit tests**

Run: `cd backend && python -m pytest -v`

Expected: All unit tests PASS, integration tests skipped.

- [ ] **Step 2: Run integration tests**

Run: `cd backend && python -m pytest -m integration -v`

Expected: All integration tests PASS.

- [ ] **Step 3: Verify Docker Compose still works**

Run: `docker compose up --build -d && sleep 5 && curl http://localhost:8000/health && docker compose down`

Expected: `{"status":"ok"}`

- [ ] **Step 4: Verify database tables**

Run: `docker compose up db -d && sleep 3 && cd backend && alembic upgrade head && docker compose exec db psql -U postgres -d nepremicnine_tracker -c "\dt" && docker compose down`

Expected: Tables `users`, `projects`, `listings`, `alembic_version` listed.

- [ ] **Step 5: Commit any remaining changes**

```bash
git status
# If anything unstaged:
git add -A && git commit -m "chore: final cleanup for Phase 1"
```
