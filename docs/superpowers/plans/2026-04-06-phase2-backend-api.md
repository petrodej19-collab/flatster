# Phase 2: Backend API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a complete backend API with JWT auth, project CRUD, listing endpoints, scraper-to-DB sync, basic investment scoring, and scheduled scraping.

**Architecture:** Feature-based router modules (auth, projects, listings) delegate to service modules (auth, scraper_sync, scoring). APScheduler runs in-process for automatic scraping. All state is in PostgreSQL.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Pydantic v2, python-jose (JWT), passlib (bcrypt), APScheduler 3.x, pytest + pytest-asyncio

---

## File Map

### New files

| File | Responsibility |
|---|---|
| `backend/app/api/__init__.py` | Package init |
| `backend/app/api/deps.py` | `get_current_user` FastAPI dependency |
| `backend/app/api/auth.py` | Auth router: register, login, me |
| `backend/app/api/projects.py` | Project CRUD router + scrape trigger |
| `backend/app/api/listings.py` | Listing query router (project-scoped) |
| `backend/app/services/__init__.py` | Package init |
| `backend/app/services/auth.py` | Password hashing, JWT creation/decoding |
| `backend/app/services/scraper_sync.py` | Upsert scraped listings, price tracking, sold detection |
| `backend/app/services/scoring.py` | Multi-factor basic scoring (0-100) |
| `backend/app/scheduler.py` | APScheduler init, register/unregister project jobs |
| `backend/app/schemas/auth.py` | Auth request/response schemas |
| `backend/app/schemas/project.py` | Project CRUD schemas |
| `backend/app/schemas/listing.py` | Listing response schemas |
| `backend/tests/test_auth_service.py` | Auth service unit tests |
| `backend/tests/test_scoring.py` | Scoring unit tests |
| `backend/tests/test_scraper_sync.py` | Scraper sync unit tests |

### Modified files

| File | Changes |
|---|---|
| `backend/app/config.py` | Add JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES, SCHEDULE_INTERVAL_HOURS, SOLD_DETECTION_MISSES |
| `backend/app/main.py` | Add lifespan (scheduler), include routers |
| `backend/requirements.txt` | Add passlib[bcrypt], python-jose[cryptography], apscheduler |

---

### Task 1: Configuration and Dependencies

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add new settings to config.py**

Add these fields to the `Settings` class in `backend/app/config.py`, after the existing `SCRAPER_MAX_RETRIES` field:

```python
    # Auth
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # Scheduler
    SCHEDULE_INTERVAL_HOURS: float = 6.0

    # Sold detection
    SOLD_DETECTION_MISSES: int = 3
```

- [ ] **Step 2: Add new dependencies to requirements.txt**

Append these lines to `backend/requirements.txt`:

```
passlib[bcrypt]>=1.7.0
python-jose[cryptography]>=3.3.0
apscheduler>=3.10.0,<4.0
```

- [ ] **Step 3: Install dependencies**

Run: `pip3 install passlib[bcrypt] python-jose[cryptography] 'apscheduler>=3.10.0,<4.0'`

- [ ] **Step 4: Verify imports work**

Run: `python3 -c "from passlib.context import CryptContext; from jose import jwt; from apscheduler.schedulers.asyncio import AsyncIOScheduler; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/requirements.txt
git commit -m "feat: add Phase 2 config settings and dependencies"
```

---

### Task 2: Auth Schemas

**Files:**
- Create: `backend/app/schemas/auth.py`

- [ ] **Step 1: Create auth schemas**

Create `backend/app/schemas/auth.py`:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


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

    model_config = {"from_attributes": True}
```

Note: `from_attributes = True` enables constructing from SQLAlchemy model instances.

- [ ] **Step 2: Verify import**

Run: `cd backend && python3 -c "from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/auth.py
git commit -m "feat: add auth request/response schemas"
```

---

### Task 3: Auth Service (TDD)

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/auth.py`
- Create: `backend/tests/test_auth_service.py`

- [ ] **Step 1: Create services package**

Create `backend/app/services/__init__.py` (empty file).

- [ ] **Step 2: Write failing tests**

Create `backend/tests/test_auth_service.py`:

```python
from uuid import uuid4

import pytest


class TestHashPassword:
    def test_returns_bcrypt_hash(self):
        from app.services.auth import hash_password

        result = hash_password("testpass123")
        assert result.startswith("$2b$")

    def test_different_passwords_different_hashes(self):
        from app.services.auth import hash_password

        h1 = hash_password("password1")
        h2 = hash_password("password2")
        assert h1 != h2


class TestVerifyPassword:
    def test_correct_password(self):
        from app.services.auth import hash_password, verify_password

        hashed = hash_password("mypassword")
        assert verify_password("mypassword", hashed) is True

    def test_wrong_password(self):
        from app.services.auth import hash_password, verify_password

        hashed = hash_password("mypassword")
        assert verify_password("wrongpassword", hashed) is False


class TestCreateAccessToken:
    def test_returns_string(self):
        from app.services.auth import create_access_token

        token = create_access_token(uuid4())
        assert isinstance(token, str)
        assert len(token) > 0

    def test_contains_three_parts(self):
        from app.services.auth import create_access_token

        token = create_access_token(uuid4())
        parts = token.split(".")
        assert len(parts) == 3


class TestDecodeAccessToken:
    def test_roundtrip(self):
        from app.services.auth import create_access_token, decode_access_token

        user_id = uuid4()
        token = create_access_token(user_id)
        decoded_id = decode_access_token(token)
        assert decoded_id == user_id

    def test_invalid_token_raises(self):
        from app.services.auth import decode_access_token

        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token("not.a.token")

    def test_expired_token_raises(self):
        from datetime import timedelta
        from app.services.auth import _create_token_with_expiry

        user_id = uuid4()
        token = _create_token_with_expiry(user_id, timedelta(seconds=-1))
        with pytest.raises(ValueError, match="Token has expired"):
            from app.services.auth import decode_access_token
            decode_access_token(token)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/test_auth_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.auth'`

- [ ] **Step 4: Implement auth service**

Create `backend/app/services/auth.py`:

```python
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: UUID) -> str:
    return _create_token_with_expiry(
        user_id, timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )


def _create_token_with_expiry(user_id: UUID, delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + delta
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> UUID:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError("Invalid token")
        return UUID(user_id)
    except ExpiredSignatureError:
        raise ValueError("Token has expired")
    except JWTError:
        raise ValueError("Invalid token")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_auth_service.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/__init__.py backend/app/services/auth.py backend/tests/test_auth_service.py
git commit -m "feat: add auth service with password hashing and JWT"
```

---

### Task 4: Auth Dependency and Router

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/auth.py`

- [ ] **Step 1: Create api package**

Create `backend/app/api/__init__.py` (empty file).

- [ ] **Step 2: Create auth dependency**

Create `backend/app/api/deps.py`:

```python
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.user import User
from app.services.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        user_id = decode_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
```

- [ ] **Step 3: Create auth router**

Create `backend/app/api/auth.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import create_access_token, hash_password, verify_password

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.email == body.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(email=body.email, password_hash=hash_password(body.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
```

- [ ] **Step 4: Verify imports**

Run: `cd backend && python3 -c "from app.api.auth import router; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/__init__.py backend/app/api/deps.py backend/app/api/auth.py
git commit -m "feat: add auth router with register, login, and me endpoints"
```

---

### Task 5: Project Schemas

**Files:**
- Create: `backend/app/schemas/project.py`

- [ ] **Step 1: Create project schemas**

Create `backend/app/schemas/project.py`:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.scraper import ProjectFilters


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
    filters: dict
    scrape_url: str
    is_active: bool
    ai_scoring_enabled: bool
    last_scraped_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python3 -c "from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/project.py
git commit -m "feat: add project CRUD schemas"
```

---

### Task 6: Project Router

**Files:**
- Create: `backend/app/api/projects.py`

- [ ] **Step 1: Create project router**

Create `backend/app/api/projects.py`:

```python
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_session
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.scraper import ProjectFilters
from app.scraper.url_builder import build_scrape_url

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_user_project(
    project_id: str,
    user: User,
    session: AsyncSession,
) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    scrape_url = build_scrape_url(body.filters)
    project = Project(
        user_id=current_user.id,
        name=body.name,
        filters=body.filters.model_dump(),
        scrape_url=scrape_url,
        is_active=body.is_active,
        ai_scoring_enabled=body.ai_scoring_enabled,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)

    if project.is_active and hasattr(request.app.state, "scheduler"):
        from app.scheduler import register_project_job

        register_project_job(request.app.state.scheduler, project.id)

    return project


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Project).where(Project.user_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await _get_user_project(project_id, current_user, session)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = await _get_user_project(project_id, current_user, session)
    update_data = body.model_dump(exclude_unset=True)

    if "filters" in update_data:
        filters = ProjectFilters(**update_data["filters"])
        project.filters = filters.model_dump()
        project.scrape_url = build_scrape_url(filters)
    if "name" in update_data:
        project.name = update_data["name"]
    if "is_active" in update_data:
        old_active = project.is_active
        project.is_active = update_data["is_active"]
        if hasattr(request.app.state, "scheduler"):
            from app.scheduler import register_project_job, unregister_project_job

            if not old_active and project.is_active:
                register_project_job(request.app.state.scheduler, project.id)
            elif old_active and not project.is_active:
                unregister_project_job(request.app.state.scheduler, project.id)
    if "ai_scoring_enabled" in update_data:
        project.ai_scoring_enabled = update_data["ai_scoring_enabled"]

    await session.commit()
    await session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = await _get_user_project(project_id, current_user, session)

    if hasattr(request.app.state, "scheduler"):
        from app.scheduler import unregister_project_job

        unregister_project_job(request.app.state.scheduler, project.id)

    await session.delete(project)
    await session.commit()


@router.post("/{project_id}/scrape")
async def trigger_scrape(
    project_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = await _get_user_project(project_id, current_user, session)
    filters = ProjectFilters(**project.filters)

    from app.scraper.scraper import scrape_project
    from app.services.scraper_sync import sync_scraped_listings

    scraped = await scrape_project(filters, settings)

    scrape_complete = len(scraped) > 0
    result = await sync_scraped_listings(session, project.id, scraped, scrape_complete)

    from datetime import datetime, timezone

    project.last_scraped_at = datetime.now(timezone.utc)
    await session.commit()

    return {
        "listings_found": result.listings_found,
        "new": result.new,
        "updated": result.updated,
        "marked_sold": result.marked_sold,
    }
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python3 -c "from app.api.projects import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/projects.py
git commit -m "feat: add project CRUD router with scrape trigger"
```

---

### Task 7: Listing Schemas

**Files:**
- Create: `backend/app/schemas/listing.py`

- [ ] **Step 1: Create listing schemas**

Create `backend/app/schemas/listing.py`:

```python
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, computed_field


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
    first_seen_at: datetime | None
    images: list[str] = []

    @computed_field
    @property
    def thumbnail_url(self) -> str | None:
        return self.images[0] if self.images else None

    model_config = {"from_attributes": True}


class ListingDetail(BaseModel):
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
    first_seen_at: datetime | None
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

    model_config = {"from_attributes": True}


class PaginatedListings(BaseModel):
    items: list[ListingSummary]
    total: int
    page: int
    per_page: int
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python3 -c "from app.schemas.listing import ListingSummary, ListingDetail, PaginatedListings; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/listing.py
git commit -m "feat: add listing response schemas with pagination"
```

---

### Task 8: Listings Router

**Files:**
- Create: `backend/app/api/listings.py`

- [ ] **Step 1: Create listings router**

Create `backend/app/api/listings.py`:

```python
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.listing import Listing
from app.models.project import Project
from app.models.user import User
from app.schemas.listing import ListingDetail, ListingSummary, PaginatedListings

router = APIRouter()


async def _verify_project_ownership(
    project_id: str,
    user: User,
    session: AsyncSession,
) -> None:
    result = await session.execute(
        select(Project.id).where(Project.id == project_id, Project.user_id == user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.get("/{project_id}/listings", response_model=PaginatedListings)
async def list_listings(
    project_id: str,
    status_filter: str | None = Query(None, alias="status"),
    min_price: float | None = None,
    max_price: float | None = None,
    min_size: float | None = None,
    max_size: float | None = None,
    sort_by: Literal["price", "size_m2", "basic_score", "first_seen_at", "price_per_m2"] = "first_seen_at",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _verify_project_ownership(project_id, current_user, session)

    query = select(Listing).where(Listing.project_id == project_id)

    if status_filter:
        query = query.where(Listing.status == status_filter)
    if min_price is not None:
        query = query.where(Listing.price >= min_price)
    if max_price is not None:
        query = query.where(Listing.price <= max_price)
    if min_size is not None:
        query = query.where(Listing.size_m2 >= min_size)
    if max_size is not None:
        query = query.where(Listing.size_m2 <= max_size)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Sort
    sort_column = getattr(Listing, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc().nulls_last())
    else:
        query = query.order_by(sort_column.asc().nulls_last())

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    listings = result.scalars().all()

    return PaginatedListings(
        items=[ListingSummary.model_validate(l) for l in listings],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{project_id}/listings/{listing_id}", response_model=ListingDetail)
async def get_listing(
    project_id: str,
    listing_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _verify_project_ownership(project_id, current_user, session)

    result = await session.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.project_id == project_id,
        )
    )
    listing = result.scalar_one_or_none()
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    return ListingDetail.model_validate(listing)
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python3 -c "from app.api.listings import router; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/listings.py
git commit -m "feat: add listings router with filtering and pagination"
```

---

### Task 9: Scraper Sync Service (TDD)

**Files:**
- Create: `backend/app/services/scraper_sync.py`
- Create: `backend/tests/test_scraper_sync.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_scraper_sync.py`:

```python
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.schemas.scraper import ScrapedListing


def _make_scraped(external_id: str = "123", price: Decimal | None = Decimal("100000")) -> ScrapedListing:
    return ScrapedListing(
        external_id=external_id,
        url=f"https://example.com/{external_id}",
        title=f"Listing {external_id}",
        price=price,
        size_m2=Decimal("50.00"),
    )


def _make_listing_model(external_id: str = "123", price: Decimal | None = Decimal("100000"), status: str = "active"):
    """Create a mock listing model object."""
    listing = MagicMock()
    listing.external_id = external_id
    listing.price = price
    listing.status = status
    listing.consecutive_misses = 0
    listing.price_history = [{"price": str(price), "date": "2026-04-01"}] if price else []
    listing.last_seen_at = datetime(2026, 4, 1, tzinfo=timezone.utc)
    listing.marked_sold_at = None
    return listing


class TestSyncResult:
    def test_sync_result_fields(self):
        from app.services.scraper_sync import SyncResult

        result = SyncResult(listings_found=10, new=5, updated=3, marked_sold=2)
        assert result.listings_found == 10
        assert result.new == 5
        assert result.updated == 3
        assert result.marked_sold == 2


class TestClassifyListings:
    def test_new_listing(self):
        from app.services.scraper_sync import _classify_listing

        action, _ = _classify_listing(_make_scraped(), existing=None)
        assert action == "new"

    def test_existing_same_price(self):
        from app.services.scraper_sync import _classify_listing

        scraped = _make_scraped(price=Decimal("100000"))
        existing = _make_listing_model(price=Decimal("100000"))
        action, _ = _classify_listing(scraped, existing)
        assert action == "unchanged"

    def test_existing_price_changed(self):
        from app.services.scraper_sync import _classify_listing

        scraped = _make_scraped(price=Decimal("90000"))
        existing = _make_listing_model(price=Decimal("100000"))
        action, _ = _classify_listing(scraped, existing)
        assert action == "price_changed"

    def test_price_none_to_value(self):
        from app.services.scraper_sync import _classify_listing

        scraped = _make_scraped(price=Decimal("100000"))
        existing = _make_listing_model(price=None)
        action, _ = _classify_listing(scraped, existing)
        assert action == "price_changed"


class TestShouldMarkSold:
    def test_below_threshold(self):
        from app.services.scraper_sync import _should_mark_sold

        assert _should_mark_sold(consecutive_misses=2, threshold=3) is False

    def test_at_threshold(self):
        from app.services.scraper_sync import _should_mark_sold

        assert _should_mark_sold(consecutive_misses=3, threshold=3) is True

    def test_above_threshold(self):
        from app.services.scraper_sync import _should_mark_sold

        assert _should_mark_sold(consecutive_misses=5, threshold=3) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/test_scraper_sync.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.scraper_sync'`

- [ ] **Step 3: Implement scraper sync service**

Create `backend/app/services/scraper_sync.py`:

```python
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.listing import Listing
from app.schemas.scraper import ScrapedListing

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    listings_found: int
    new: int
    updated: int
    marked_sold: int


def _classify_listing(
    scraped: ScrapedListing, existing: Listing | None
) -> tuple[str, Decimal | None]:
    """Classify a scraped listing as 'new', 'unchanged', or 'price_changed'.

    Returns (action, old_price).
    """
    if existing is None:
        return "new", None

    old_price = existing.price
    new_price = scraped.price

    if old_price != new_price:
        return "price_changed", old_price

    return "unchanged", old_price


def _should_mark_sold(consecutive_misses: int, threshold: int) -> bool:
    return consecutive_misses >= threshold


async def sync_scraped_listings(
    session: AsyncSession,
    project_id,
    scraped: list[ScrapedListing],
    scrape_complete: bool,
) -> SyncResult:
    now = datetime.now(timezone.utc)
    today = date.today().isoformat()

    # Load existing listings for this project into a lookup dict
    result = await session.execute(
        select(Listing).where(Listing.project_id == project_id)
    )
    existing_map: dict[str, Listing] = {
        l.external_id: l for l in result.scalars().all()
    }

    seen_external_ids: set[str] = set()
    new_count = 0
    updated_count = 0

    for item in scraped:
        seen_external_ids.add(item.external_id)
        existing = existing_map.get(item.external_id)
        action, old_price = _classify_listing(item, existing)

        if action == "new":
            listing = Listing(
                project_id=project_id,
                external_id=item.external_id,
                url=item.url,
                title=item.title,
                location=item.location,
                region=item.region,
                property_type=item.property_type,
                transaction_type=item.transaction_type,
                price=item.price,
                price_per_m2=item.price_per_m2,
                size_m2=item.size_m2,
                rooms=item.rooms,
                year_built=item.year_built,
                year_renovated=item.year_renovated,
                floor=item.floor,
                land_size_m2=item.land_size_m2,
                energy_class=item.energy_class,
                description=item.description,
                images=item.images,
                agency=item.agency,
                status="active",
                price_history=[{"price": str(item.price), "date": today}] if item.price else [],
                consecutive_misses=0,
                first_seen_at=now,
                last_seen_at=now,
            )
            session.add(listing)
            new_count += 1

        elif action == "price_changed":
            existing.price = item.price
            existing.price_per_m2 = item.price_per_m2
            existing.size_m2 = item.size_m2 or existing.size_m2
            existing.description = item.description or existing.description
            existing.images = item.images if item.images else existing.images
            existing.year_built = item.year_built or existing.year_built
            existing.year_renovated = item.year_renovated or existing.year_renovated
            existing.floor = item.floor or existing.floor
            existing.energy_class = item.energy_class or existing.energy_class
            existing.status = "price_changed"
            existing.consecutive_misses = 0
            existing.last_seen_at = now
            history = list(existing.price_history)
            history.append({"price": str(item.price), "date": today})
            existing.price_history = history
            updated_count += 1

        else:  # unchanged
            existing.consecutive_misses = 0
            existing.last_seen_at = now
            # Also update fields that might have been missing before
            existing.description = item.description or existing.description
            existing.images = item.images if item.images else existing.images
            existing.energy_class = item.energy_class or existing.energy_class
            existing.year_renovated = item.year_renovated or existing.year_renovated

    # Sold detection — only when scrape was complete
    marked_sold = 0
    if scrape_complete:
        for ext_id, listing in existing_map.items():
            if ext_id not in seen_external_ids and listing.status in ("active", "price_changed"):
                listing.consecutive_misses += 1
                if _should_mark_sold(listing.consecutive_misses, settings.SOLD_DETECTION_MISSES):
                    listing.status = "sold"
                    listing.marked_sold_at = now
                    marked_sold += 1

    await session.commit()

    # Trigger scoring
    from app.services.scoring import score_project_listings

    await score_project_listings(session, project_id)

    return SyncResult(
        listings_found=len(scraped),
        new=new_count,
        updated=updated_count,
        marked_sold=marked_sold,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_scraper_sync.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/scraper_sync.py backend/tests/test_scraper_sync.py
git commit -m "feat: add scraper sync service with price tracking and sold detection"
```

---

### Task 10: Basic Scoring Service (TDD)

**Files:**
- Create: `backend/app/services/scoring.py`
- Create: `backend/tests/test_scoring.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_scoring.py`:

```python
from decimal import Decimal

import pytest


class TestScorePricePerM2:
    def test_at_average(self):
        from app.services.scoring import _score_price_per_m2

        assert _score_price_per_m2(Decimal("2000"), Decimal("2000")) == Decimal("50")

    def test_half_average(self):
        from app.services.scoring import _score_price_per_m2

        assert _score_price_per_m2(Decimal("1000"), Decimal("2000")) == Decimal("100")

    def test_double_average(self):
        from app.services.scoring import _score_price_per_m2

        assert _score_price_per_m2(Decimal("4000"), Decimal("2000")) == Decimal("0")

    def test_none_returns_neutral(self):
        from app.services.scoring import _score_price_per_m2

        assert _score_price_per_m2(None, Decimal("2000")) == Decimal("50")

    def test_zero_average_returns_neutral(self):
        from app.services.scoring import _score_price_per_m2

        assert _score_price_per_m2(Decimal("2000"), Decimal("0")) == Decimal("50")


class TestScoreYear:
    def test_new_building(self):
        from app.services.scoring import _score_year

        assert _score_year(2024, None) == Decimal("100")

    def test_old_building(self):
        from app.services.scoring import _score_year

        assert _score_year(1940, None) == Decimal("0")

    def test_renovated_takes_precedence(self):
        from app.services.scoring import _score_year

        score_old = _score_year(1960, None)
        score_renovated = _score_year(1960, 2015)
        assert score_renovated > score_old

    def test_none_returns_neutral(self):
        from app.services.scoring import _score_year

        assert _score_year(None, None) == Decimal("50")


class TestScoreSize:
    def test_at_average(self):
        from app.services.scoring import _score_size

        assert _score_size(Decimal("60"), Decimal("60")) == Decimal("50")

    def test_double_average(self):
        from app.services.scoring import _score_size

        assert _score_size(Decimal("120"), Decimal("60")) == Decimal("100")

    def test_none_returns_neutral(self):
        from app.services.scoring import _score_size

        assert _score_size(None, Decimal("60")) == Decimal("50")


class TestScoreEnergyClass:
    def test_a1(self):
        from app.services.scoring import _score_energy_class

        assert _score_energy_class("A1") == Decimal("100")

    def test_d(self):
        from app.services.scoring import _score_energy_class

        assert _score_energy_class("D") == Decimal("40")

    def test_none_returns_neutral(self):
        from app.services.scoring import _score_energy_class

        assert _score_energy_class(None) == Decimal("50")


class TestScoreFloor:
    def test_middle_floor(self):
        from app.services.scoring import _score_floor

        assert _score_floor("2/4") == Decimal("100")

    def test_ground_floor(self):
        from app.services.scoring import _score_floor

        # Ground floor: 0/X or pritličje
        assert _score_floor("pritličje") == Decimal("60")

    def test_top_floor(self):
        from app.services.scoring import _score_floor

        assert _score_floor("4/4") == Decimal("80")

    def test_none_returns_neutral(self):
        from app.services.scoring import _score_floor

        assert _score_floor(None) == Decimal("50")


class TestCalculateScore:
    def test_returns_weighted_sum(self):
        from app.services.scoring import calculate_listing_score

        score = calculate_listing_score(
            price_per_m2=Decimal("2000"),
            avg_price_per_m2=Decimal("2000"),
            year_built=2020,
            year_renovated=None,
            size_m2=Decimal("60"),
            avg_size=Decimal("60"),
            energy_class=None,
            floor=None,
        )
        # All at average/neutral = 50 for each factor
        assert score == Decimal("50.00")

    def test_perfect_listing(self):
        from app.services.scoring import calculate_listing_score

        score = calculate_listing_score(
            price_per_m2=Decimal("1000"),
            avg_price_per_m2=Decimal("2000"),
            year_built=2024,
            year_renovated=None,
            size_m2=Decimal("120"),
            avg_size=Decimal("60"),
            energy_class="A1",
            floor="2/4",
        )
        assert score == Decimal("100.00")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python3 -m pytest tests/test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.scoring'`

- [ ] **Step 3: Implement scoring service**

Create `backend/app/services/scoring.py`:

```python
import logging
import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing

logger = logging.getLogger(__name__)

NEUTRAL = Decimal("50")

# Weights
W_PRICE = Decimal("0.40")
W_YEAR = Decimal("0.25")
W_SIZE = Decimal("0.15")
W_ENERGY = Decimal("0.10")
W_FLOOR = Decimal("0.10")


def _clamp(value: Decimal) -> Decimal:
    if value < 0:
        return Decimal("0")
    if value > 100:
        return Decimal("100")
    return value


def _score_price_per_m2(
    price_per_m2: Decimal | None, avg: Decimal | None
) -> Decimal:
    if price_per_m2 is None or avg is None or avg == 0:
        return NEUTRAL
    # 100 at half average, 50 at average, 0 at double average
    ratio = price_per_m2 / avg
    score = Decimal("100") * (Decimal("2") - ratio)
    return _clamp(score.quantize(Decimal("1")))


def _score_year(year_built: int | None, year_renovated: int | None) -> Decimal:
    year = None
    if year_built and year_renovated:
        year = max(year_built, year_renovated)
    elif year_built:
        year = year_built
    elif year_renovated:
        year = year_renovated

    if year is None:
        return NEUTRAL

    # 100 = 2020+, 0 = pre-1950, linear
    if year >= 2020:
        return Decimal("100")
    if year <= 1950:
        return Decimal("0")
    score = Decimal(str((year - 1950))) / Decimal("70") * Decimal("100")
    return _clamp(score.quantize(Decimal("1")))


def _score_size(size: Decimal | None, avg: Decimal | None) -> Decimal:
    if size is None or avg is None or avg == 0:
        return NEUTRAL
    # 100 at 2x average, 50 at average, 0 at half or less
    ratio = size / avg
    score = Decimal("100") * (ratio - Decimal("0.5")) / Decimal("1.5")
    return _clamp(score.quantize(Decimal("1")))


def _score_energy_class(energy_class: str | None) -> Decimal:
    if energy_class is None:
        return NEUTRAL
    mapping = {
        "A1": Decimal("100"),
        "A2": Decimal("100"),
        "B1": Decimal("80"),
        "B2": Decimal("80"),
        "C": Decimal("60"),
        "D": Decimal("40"),
        "E": Decimal("20"),
        "F": Decimal("0"),
        "G": Decimal("0"),
    }
    return mapping.get(energy_class.upper(), NEUTRAL)


def _score_floor(floor: str | None) -> Decimal:
    if floor is None:
        return NEUTRAL

    if floor.lower() == "pritličje":
        return Decimal("60")

    match = re.match(r"(\d+)/(\d+)", floor)
    if not match:
        return NEUTRAL

    current = int(match.group(1))
    total = int(match.group(2))

    if current == 0:
        return Decimal("60")
    if total > 0 and current == total:
        return Decimal("80")
    # Middle floors
    return Decimal("100")


def calculate_listing_score(
    price_per_m2: Decimal | None,
    avg_price_per_m2: Decimal | None,
    year_built: int | None,
    year_renovated: int | None,
    size_m2: Decimal | None,
    avg_size: Decimal | None,
    energy_class: str | None,
    floor: str | None,
) -> Decimal:
    score = (
        W_PRICE * _score_price_per_m2(price_per_m2, avg_price_per_m2)
        + W_YEAR * _score_year(year_built, year_renovated)
        + W_SIZE * _score_size(size_m2, avg_size)
        + W_ENERGY * _score_energy_class(energy_class)
        + W_FLOOR * _score_floor(floor)
    )
    return score.quantize(Decimal("0.01"))


async def score_project_listings(session: AsyncSession, project_id) -> None:
    result = await session.execute(
        select(Listing).where(
            Listing.project_id == project_id,
            Listing.status.in_(["active", "price_changed"]),
        )
    )
    listings = result.scalars().all()

    if not listings:
        return

    # Compute averages from listings that have the data
    prices = [l.price_per_m2 for l in listings if l.price_per_m2 is not None]
    sizes = [l.size_m2 for l in listings if l.size_m2 is not None]

    avg_price = sum(prices) / len(prices) if prices else None
    avg_size = sum(sizes) / len(sizes) if sizes else None

    for listing in listings:
        listing.basic_score = calculate_listing_score(
            price_per_m2=listing.price_per_m2,
            avg_price_per_m2=avg_price,
            year_built=listing.year_built,
            year_renovated=listing.year_renovated,
            size_m2=listing.size_m2,
            avg_size=avg_size,
            energy_class=listing.energy_class,
            floor=listing.floor,
        )

    await session.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_scoring.py -v`
Expected: 17 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/scoring.py backend/tests/test_scoring.py
git commit -m "feat: add multi-factor basic scoring service"
```

---

### Task 11: Scheduler

**Files:**
- Create: `backend/app/scheduler.py`

- [ ] **Step 1: Create scheduler module**

Create `backend/app/scheduler.py`:

```python
import logging
from datetime import datetime, timezone
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

_session_factory: async_sessionmaker | None = None


async def init_scheduler(session_factory: async_sessionmaker) -> AsyncIOScheduler:
    global _session_factory
    _session_factory = session_factory

    scheduler = AsyncIOScheduler()

    async with session_factory() as session:
        from app.models.project import Project

        result = await session.execute(
            select(Project).where(Project.is_active == True)  # noqa: E712
        )
        projects = result.scalars().all()

        for project in projects:
            register_project_job(scheduler, project.id)
            logger.info("Registered scrape job for project %s", project.id)

    logger.info("Scheduler initialized with %d active projects", len(projects))
    return scheduler


def register_project_job(scheduler: AsyncIOScheduler, project_id: UUID) -> None:
    job_id = f"scrape_{project_id}"

    # Remove existing job if any
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        _run_project_scrape,
        "interval",
        hours=settings.SCHEDULE_INTERVAL_HOURS,
        id=job_id,
        args=[project_id],
        jitter=600,  # +/- 10 minutes
        replace_existing=True,
    )


def unregister_project_job(scheduler: AsyncIOScheduler, project_id: UUID) -> None:
    job_id = f"scrape_{project_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


async def _run_project_scrape(project_id: UUID) -> None:
    if _session_factory is None:
        logger.error("Session factory not initialized")
        return

    try:
        async with _session_factory() as session:
            from app.models.project import Project
            from app.schemas.scraper import ProjectFilters
            from app.scraper.scraper import scrape_project
            from app.services.scraper_sync import sync_scraped_listings

            result = await session.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            if project is None:
                logger.warning("Project %s not found, skipping scrape", project_id)
                return

            if not project.is_active:
                logger.info("Project %s is inactive, skipping scrape", project_id)
                return

            filters = ProjectFilters(**project.filters)
            logger.info("Starting scheduled scrape for project %s", project_id)

            scraped = await scrape_project(filters, settings)
            scrape_complete = len(scraped) > 0

            sync_result = await sync_scraped_listings(
                session, project.id, scraped, scrape_complete
            )

            project.last_scraped_at = datetime.now(timezone.utc)
            await session.commit()

            logger.info(
                "Scheduled scrape for project %s complete: %d found, %d new, %d updated, %d sold",
                project_id,
                sync_result.listings_found,
                sync_result.new,
                sync_result.updated,
                sync_result.marked_sold,
            )

    except Exception:
        logger.exception("Scheduled scrape failed for project %s", project_id)
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python3 -c "from app.scheduler import init_scheduler, register_project_job, unregister_project_job; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/scheduler.py
git commit -m "feat: add APScheduler for automatic project scraping"
```

---

### Task 12: Wire Up main.py

**Files:**
- Modify: `backend/app/main.py`

- [ ] **Step 1: Update main.py with lifespan and routers**

Replace the entire contents of `backend/app/main.py` with:

```python
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.listings import router as listings_router
from app.api.projects import router as projects_router
from app.database import async_session
from app.scheduler import init_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = await init_scheduler(async_session)
    app.state.scheduler = scheduler
    scheduler.start()
    logger.info("Scheduler started")
    yield
    scheduler.shutdown()
    logger.info("Scheduler shut down")


app = FastAPI(title="NepremicnineTracker", version="0.2.0", lifespan=lifespan)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(listings_router, prefix="/api/projects", tags=["listings"])


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python3 -c "from app.main import app; print('OK')"`

Note: This will fail if the database is not available (scheduler init tries to query projects). That's expected — the import test validates syntax and module resolution. Full integration testing requires Docker.

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: wire up routers and scheduler in main.py"
```

---

### Task 13: Add Cascade Delete to Project Model

**Files:**
- Modify: `backend/app/models/project.py`

The `DELETE /api/projects/{id}` endpoint needs cascade delete to remove associated listings. Add a relationship to the Project model.

- [ ] **Step 1: Add relationship to Project model**

Add to the imports in `backend/app/models/project.py`:

```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
```

(Replace the existing `from sqlalchemy.orm import Mapped, mapped_column` import.)

Add after the `last_scraped_at` field:

```python
    listings: Mapped[list["Listing"]] = relationship(
        "Listing", back_populates="project", cascade="all, delete-orphan"
    )
```

- [ ] **Step 2: Add back-reference to Listing model**

Add to the imports in `backend/app/models/listing.py`:

```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
```

(Replace the existing `from sqlalchemy.orm import Mapped, mapped_column` import.)

Add after the `project_id` field:

```python
    project: Mapped["Project"] = relationship("Project", back_populates="listings")
```

- [ ] **Step 3: Verify imports**

Run: `cd backend && python3 -c "from app.models.project import Project; from app.models.listing import Listing; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Run existing tests to verify nothing broke**

Run: `cd backend && python3 -m pytest -v`
Expected: All existing tests still pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/project.py backend/app/models/listing.py
git commit -m "feat: add cascade delete relationship between Project and Listing"
```

---

### Task 14: Run Full Test Suite

**Files:** None (verification only)

- [ ] **Step 1: Run all tests**

Run: `cd backend && python3 -m pytest -v`
Expected: All tests pass (auth service: 8, scoring: 17, scraper sync: 7, plus all existing Phase 1 tests).

- [ ] **Step 2: Verify total test count**

Expected total: ~71 tests (39 Phase 1 + 8 auth + 17 scoring + 7 sync), 3 deselected (integration).

If any tests fail, fix them before proceeding.

---

### Task 15: Update Alembic Migration

**Files:**
- Modify: `backend/alembic/versions/74bc0191d77a_initial_schema.py`

No schema changes are needed — the `basic_score`, `ai_score`, `price_history`, `consecutive_misses`, and all other columns were already created in the Phase 1 migration. This task is a verification step.

- [ ] **Step 1: Verify migration covers all columns used by Phase 2**

Read `backend/alembic/versions/74bc0191d77a_initial_schema.py` and confirm these columns exist in the `listings` table:
- `basic_score` (Numeric 5,2)
- `price_history` (JSONB)
- `consecutive_misses` (Integer)
- `status` (String 20)
- `marked_sold_at` (DateTime)
- `first_seen_at` (DateTime)
- `last_seen_at` (DateTime)

All present — no migration changes needed.

- [ ] **Step 2: Commit (skip if no changes)**

No commit needed — migration is already complete.
