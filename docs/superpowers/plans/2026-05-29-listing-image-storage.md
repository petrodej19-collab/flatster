# Listing Image Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store the first three images of each listing as resized WebP bytes in Postgres so the frontend serves images from our backend instead of `img.nepremicnine.net`.

**Architecture:** New `listing_image` table keyed on `(listing_id, position)` holds the original `source_url` and lazily-fetched `image_data` bytes. A new backend endpoint serves bytes, fetching + resizing + caching on first request. The listings API response replaces `images` URLs with backend URLs. Existing `listing.images` JSONB stays as the legacy source-of-truth.

**Tech Stack:** FastAPI / SQLAlchemy async / Alembic / Postgres / Pillow / httpx; React + TanStack Query frontend.

**Spec:** `docs/superpowers/specs/2026-05-29-listing-image-storage-design.md`

---

## File Structure

- Modify: `backend/requirements.txt` — add `Pillow`, `httpx`.
- Create: `backend/app/models/listing_image.py` — SQLAlchemy model.
- Create: `backend/alembic/versions/<rev>_add_listing_image.py` — schema + data backfill.
- Create: `backend/app/services/image_fetcher.py` — fetch, resize, encode WebP. Pure-ish module.
- Modify: `backend/app/api/listings.py` — new image-serving endpoint; rebuild `images` field in list/detail responses.
- Modify: `backend/app/services/scraper_sync.py` — upsert `listing_image` rows during sync.
- Create: `backend/tests/test_image_fetcher.py` — unit tests for the resize step.
- Create: `backend/tests/test_listing_image_endpoint.py` — endpoint state-machine tests with mocked DB session + httpx.

---

## Task 1: Add Pillow and httpx dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Read current requirements.txt**

```bash
cat backend/requirements.txt
```

Note whether `httpx` and `Pillow` already appear (they may be transitive but not pinned).

- [ ] **Step 2: Add the lines**

Append to `backend/requirements.txt` (or insert in alphabetical position if the file is sorted):

```
Pillow>=10.0
httpx>=0.27
```

- [ ] **Step 3: Rebuild the app image**

```bash
docker compose build app
docker compose up -d app
```

- [ ] **Step 4: Verify imports work in the container**

```bash
docker compose exec app python -c "from PIL import Image; import httpx; print(Image.__version__, httpx.__version__)"
```

Expected: two version numbers print without errors.

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt
git commit -m "Add Pillow and httpx for listing image storage"
```

---

## Task 2: ListingImage model

**Files:**
- Create: `backend/app/models/listing_image.py`

- [ ] **Step 1: Create the model**

```python
# backend/app/models/listing_image.py
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, LargeBinary, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ListingImage(Base):
    __tablename__ = "listing_images"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    mime_type: Mapped[str | None] = mapped_column(Text, default=None)
    fetched_at: Mapped[datetime | None] = mapped_column(default=None)
    fetch_failed_at: Mapped[datetime | None] = mapped_column(default=None)
```

Note: `Base` provides only the declarative base — no `UUIDMixin` / `TimestampMixin` since the PK is composite and no `created_at` is needed.

- [ ] **Step 2: Verify the model imports**

```bash
docker compose exec app python -c "from app.models.listing_image import ListingImage; print(ListingImage.__tablename__)"
```

Expected: `listing_images`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/models/listing_image.py
git commit -m "Add ListingImage SQLAlchemy model"
```

---

## Task 3: Alembic migration with data backfill

**Files:**
- Create: `backend/alembic/versions/<new_rev>_add_listing_images.py`

- [ ] **Step 1: Generate a revision file**

```bash
docker compose exec app alembic revision -m "add listing_images table"
```

Note the generated filename (e.g., `c4d5e6f7a8b9_add_listing_images.py`).

- [ ] **Step 2: Replace the revision's body**

Open the new file. Keep its auto-generated `revision` and `down_revision` values; replace `upgrade()` and `downgrade()`:

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    op.create_table(
        "listing_images",
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=True),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetch_failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("listing_id", "position"),
    )

    op.execute(
        """
        INSERT INTO listing_images (listing_id, position, source_url)
        SELECT l.id, idx - 1, l.images->>(idx - 1)
        FROM listings l
        JOIN LATERAL generate_series(
            1, LEAST(jsonb_array_length(l.images), 3)
        ) AS idx ON TRUE
        WHERE jsonb_array_length(l.images) > 0
        """
    )


def downgrade() -> None:
    op.drop_table("listing_images")
```

- [ ] **Step 3: Run the migration**

```bash
docker compose exec app alembic upgrade head
```

Expected: no errors.

- [ ] **Step 4: Verify the table and backfill**

```bash
docker compose exec db psql -U postgres -d nepremicnine_tracker -c "
  SELECT COUNT(*) AS total_rows,
         COUNT(DISTINCT listing_id) AS listings_covered
  FROM listing_images;
"
```

Expected: `total_rows` > 0 and `listings_covered` roughly matches the number of listings that have at least one image. Spot-check:

```bash
docker compose exec db psql -U postgres -d nepremicnine_tracker -c "
  SELECT listing_id, position, source_url
  FROM listing_images
  ORDER BY listing_id, position
  LIMIT 6;
"
```

Expected: positions 0/1/2 per listing, `source_url` matches `img.nepremicnine.net/...`.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/<new_rev>_add_listing_images.py
git commit -m "Add listing_images table and backfill from listings.images JSONB"
```

---

## Task 4: Image fetcher — pure resize/encode step

**Files:**
- Create: `backend/app/services/image_fetcher.py`
- Create: `backend/tests/test_image_fetcher.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_image_fetcher.py`:

```python
from io import BytesIO

from PIL import Image

from app.services.image_fetcher import encode_webp


def _make_jpeg(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def test_encode_webp_resizes_wide_image_to_max_800():
    raw = _make_jpeg(1600, 1200)
    out = encode_webp(raw, max_width=800)
    img = Image.open(BytesIO(out))
    assert img.format == "WEBP"
    assert img.width == 800
    assert img.height == 600


def test_encode_webp_leaves_small_image_unscaled():
    raw = _make_jpeg(400, 300)
    out = encode_webp(raw, max_width=800)
    img = Image.open(BytesIO(out))
    assert img.format == "WEBP"
    assert img.width == 400
    assert img.height == 300


def test_encode_webp_handles_png_input():
    img = Image.new("RGB", (1200, 900), color=(10, 20, 30))
    buf = BytesIO()
    img.save(buf, format="PNG")
    out = encode_webp(buf.getvalue(), max_width=800)
    assert Image.open(BytesIO(out)).format == "WEBP"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec app pytest tests/test_image_fetcher.py -v
```

Expected: ImportError on `encode_webp`.

- [ ] **Step 3: Implement `encode_webp`**

`backend/app/services/image_fetcher.py`:

```python
from io import BytesIO

from PIL import Image


def encode_webp(raw: bytes, max_width: int = 800, quality: int = 80) -> bytes:
    """Decode raw image bytes, downscale if wider than max_width, return WebP bytes."""
    img = Image.open(BytesIO(raw))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    if img.width > max_width:
        new_height = round(img.height * max_width / img.width)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
    out = BytesIO()
    img.save(out, format="WEBP", quality=quality, method=4)
    return out.getvalue()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
docker compose exec app pytest tests/test_image_fetcher.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/image_fetcher.py backend/tests/test_image_fetcher.py
git commit -m "Add encode_webp helper for listing-image storage"
```

---

## Task 5: Image fetcher — fetch_and_store async function

**Files:**
- Modify: `backend/app/services/image_fetcher.py`
- Modify: `backend/tests/test_image_fetcher.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_image_fetcher.py`:

```python
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services.image_fetcher import fetch_and_store


class _FakeRow:
    def __init__(self, source_url):
        self.source_url = source_url
        self.image_data = None
        self.mime_type = None
        self.fetched_at = None
        self.fetch_failed_at = None


@pytest.mark.asyncio
async def test_fetch_and_store_success(monkeypatch):
    row = _FakeRow("https://example.com/a.jpg")
    session = MagicMock()
    session.commit = AsyncMock()

    raw = _make_jpeg(400, 300)
    mock_resp = MagicMock(status_code=200, content=raw)
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: mock_client)

    result = await fetch_and_store(session, row)
    assert result is not None
    assert row.image_data is not None
    assert row.mime_type == "image/webp"
    assert isinstance(row.fetched_at, datetime)
    assert row.fetch_failed_at is None
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_and_store_marks_tombstone_on_404(monkeypatch):
    row = _FakeRow("https://example.com/dead.jpg")
    session = MagicMock()
    session.commit = AsyncMock()

    mock_resp = MagicMock(status_code=404, content=b"")
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: mock_client)

    result = await fetch_and_store(session, row)
    assert result is None
    assert row.image_data is None
    assert isinstance(row.fetch_failed_at, datetime)
    session.commit.assert_awaited_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec app pytest tests/test_image_fetcher.py -v
```

Expected: ImportError on `fetch_and_store`.

- [ ] **Step 3: Implement `fetch_and_store`**

Append to `backend/app/services/image_fetcher.py`:

```python
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def fetch_and_store(session: AsyncSession, row) -> bytes | None:
    """Fetch row.source_url, resize/encode, persist on the row, commit.

    On success returns the encoded WebP bytes. On HTTP failure sets
    fetch_failed_at and returns None.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(row.source_url)
    except httpx.HTTPError as exc:
        logger.warning("Image fetch failed for %s: %s", row.source_url, exc)
        row.fetch_failed_at = datetime.now(timezone.utc)
        await session.commit()
        return None

    if resp.status_code != 200 or not resp.content:
        logger.info("Image fetch non-200 for %s: %d", row.source_url, resp.status_code)
        row.fetch_failed_at = datetime.now(timezone.utc)
        await session.commit()
        return None

    try:
        encoded = encode_webp(resp.content)
    except Exception as exc:
        logger.warning("Image decode failed for %s: %s", row.source_url, exc)
        row.fetch_failed_at = datetime.now(timezone.utc)
        await session.commit()
        return None

    row.image_data = encoded
    row.mime_type = "image/webp"
    row.fetched_at = datetime.now(timezone.utc)
    await session.commit()
    return encoded
```

- [ ] **Step 4: Run test to verify it passes**

```bash
docker compose exec app pytest tests/test_image_fetcher.py -v
```

Expected: 5 passed (3 from Task 4 + 2 new).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/image_fetcher.py backend/tests/test_image_fetcher.py
git commit -m "Add async fetch_and_store for listing images"
```

---

## Task 6: Image-serving endpoint

**Files:**
- Modify: `backend/app/api/listings.py`
- Create: `backend/tests/test_listing_image_endpoint.py`

- [ ] **Step 1: Write failing tests for the endpoint state machine**

`backend/tests/test_listing_image_endpoint.py`:

```python
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.listings import serve_listing_image


def _row(image_data=None, fetch_failed_at=None, source_url="https://example.com/a.jpg"):
    r = MagicMock()
    r.image_data = image_data
    r.fetch_failed_at = fetch_failed_at
    r.source_url = source_url
    r.mime_type = "image/webp"
    r.fetched_at = datetime(2026, 5, 29, tzinfo=timezone.utc)
    return r


def _session_returning(row):
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=row)
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.mark.asyncio
async def test_404_when_no_row(monkeypatch):
    from fastapi import HTTPException

    session = _session_returning(None)
    with pytest.raises(HTTPException) as exc:
        await serve_listing_image(
            project_id="00000000-0000-0000-0000-000000000000",
            listing_id="00000000-0000-0000-0000-000000000000",
            position=0,
            session=session,
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_returns_bytes_when_cached():
    row = _row(image_data=b"cachedbytes")
    session = _session_returning(row)
    resp = await serve_listing_image(
        project_id="00000000-0000-0000-0000-000000000000",
        listing_id="00000000-0000-0000-0000-000000000000",
        position=0,
        session=session,
    )
    assert resp.body == b"cachedbytes"
    assert resp.media_type == "image/webp"


@pytest.mark.asyncio
async def test_404_when_tombstoned():
    from fastapi import HTTPException

    row = _row(image_data=None, fetch_failed_at=datetime(2026, 5, 1, tzinfo=timezone.utc))
    session = _session_returning(row)
    with pytest.raises(HTTPException) as exc:
        await serve_listing_image(
            project_id="00000000-0000-0000-0000-000000000000",
            listing_id="00000000-0000-0000-0000-000000000000",
            position=0,
            session=session,
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_lazy_fetch_on_first_call(monkeypatch):
    from app.api import listings as listings_api

    row = _row(image_data=None)
    session = _session_returning(row)
    monkeypatch.setattr(
        listings_api, "fetch_and_store", AsyncMock(return_value=b"fetchedbytes")
    )
    resp = await serve_listing_image(
        project_id="00000000-0000-0000-0000-000000000000",
        listing_id="00000000-0000-0000-0000-000000000000",
        position=0,
        session=session,
    )
    assert resp.body == b"fetchedbytes"
    assert resp.media_type == "image/webp"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
docker compose exec app pytest tests/test_listing_image_endpoint.py -v
```

Expected: ImportError on `serve_listing_image`.

- [ ] **Step 3: Implement the endpoint**

Add to `backend/app/api/listings.py`:

```python
import asyncio
from collections import defaultdict

from fastapi import Response
from sqlalchemy import select as _select

from app.models.listing_image import ListingImage
from app.services.image_fetcher import fetch_and_store

_IMAGE_CACHE_HEADERS = {
    "Cache-Control": "public, max-age=31536000, immutable",
}

# Single-flight: one in-flight fetch per (listing_id, position). The dict
# grows by one entry per image ever fetched (~75 K max for the current
# dataset) — bounded and small enough not to bother with cleanup.
_image_fetch_locks: dict[tuple[UUID, int], asyncio.Lock] = defaultdict(asyncio.Lock)


async def _load_image_row(session, listing_id: UUID, position: int):
    result = await session.execute(
        _select(ListingImage).where(
            ListingImage.listing_id == listing_id,
            ListingImage.position == position,
        )
    )
    return result.scalar_one_or_none()


@router.get("/{project_id}/listings/{listing_id}/image/{position}")
async def serve_listing_image(
    project_id: UUID,
    listing_id: UUID,
    position: int,
    session: AsyncSession = Depends(get_session),
):
    """Serve a stored listing image. Lazy-fetches on first call."""
    row = await _load_image_row(session, listing_id, position)
    if row is None:
        raise HTTPException(status_code=404, detail="image not found")
    if row.image_data is not None:
        return Response(
            content=bytes(row.image_data),
            media_type=row.mime_type or "image/webp",
            headers=_IMAGE_CACHE_HEADERS,
        )
    if row.fetch_failed_at is not None:
        raise HTTPException(status_code=404, detail="image unavailable")

    async with _image_fetch_locks[(listing_id, position)]:
        # Re-check after acquiring the lock: another coroutine may have
        # just filled in this row.
        row = await _load_image_row(session, listing_id, position)
        if row is None:
            raise HTTPException(status_code=404, detail="image not found")
        if row.image_data is not None:
            return Response(
                content=bytes(row.image_data),
                media_type=row.mime_type or "image/webp",
                headers=_IMAGE_CACHE_HEADERS,
            )
        if row.fetch_failed_at is not None:
            raise HTTPException(status_code=404, detail="image unavailable")
        data = await fetch_and_store(session, row)
        if data is None:
            raise HTTPException(status_code=404, detail="image unavailable")
        return Response(
            content=bytes(data),
            media_type="image/webp",
            headers=_IMAGE_CACHE_HEADERS,
        )
```

(Match the existing import style at the top of the file — fold these imports into the existing groups; the example uses `_select` only to avoid shadowing if `select` is already imported as something else.)

Important: this endpoint is intentionally NOT auth-gated. It uses `Depends(get_session)` only. Do not add `Depends(get_current_user)`.

- [ ] **Step 4: Run test to verify it passes**

```bash
docker compose exec app pytest tests/test_listing_image_endpoint.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Smoke-test against a real listing**

```bash
docker compose restart app
sleep 5

# Find a listing id that has images
docker compose exec db psql -U postgres -d nepremicnine_tracker -c "
  SELECT listing_id, position, source_url
  FROM listing_images
  WHERE image_data IS NULL AND fetch_failed_at IS NULL
  LIMIT 1;
"

# Fetch it via the endpoint (use the project_id from the listings table for that listing)
curl -s -o /tmp/test.webp -w "%{http_code} %{size_download}\n" \
  "http://localhost:8000/api/projects/<PROJECT_ID>/listings/<LISTING_ID>/image/0"

file /tmp/test.webp
```

Expected: `200 <some-number>` and `file` reports `Web/P image`. Second request returns the cached bytes (faster).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/listings.py backend/tests/test_listing_image_endpoint.py
git commit -m "Add listing image endpoint with lazy fetch"
```

---

## Task 7: Upsert listing_image rows during scrape sync

**Files:**
- Modify: `backend/app/services/scraper_sync.py`

- [ ] **Step 1: Locate the sync function**

Open `backend/app/services/scraper_sync.py`. Find `sync_scraped_listings` and the loop where each scraped listing is matched to an existing `Listing` row and either inserted or updated. Identify the point after a listing's row has been created (`session.add(...)`) or updated (in-place mutation).

- [ ] **Step 2: Add an upsert helper**

Near the top of `scraper_sync.py` (after imports, before classes):

```python
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.listing_image import ListingImage


async def _upsert_listing_images(
    session, listing_id, image_urls: list[str]
) -> None:
    """Sync up to the first 3 image source URLs for a listing.

    Rules:
    - For positions 0..min(len, 3)-1, insert a row or, if one exists with
      a different source_url, overwrite the whole row (bytes reset).
    - Positions beyond len(image_urls) are deleted (e.g., the listing now
      has fewer images than before).
    """
    capped = image_urls[:3]
    for position, url in enumerate(capped):
        stmt = pg_insert(ListingImage).values(
            listing_id=listing_id,
            position=position,
            source_url=url,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["listing_id", "position"],
            set_={
                "source_url": stmt.excluded.source_url,
                "image_data": None,
                "mime_type": None,
                "fetched_at": None,
                "fetch_failed_at": None,
            },
            where=ListingImage.source_url != stmt.excluded.source_url,
        )
        await session.execute(stmt)

    # Trim positions that no longer exist
    from sqlalchemy import delete
    await session.execute(
        delete(ListingImage).where(
            ListingImage.listing_id == listing_id,
            ListingImage.position >= len(capped),
        )
    )
```

- [ ] **Step 3: Call the helper from the sync loop**

In `sync_scraped_listings`, after the existing logic that creates or updates the `Listing` row (and after the `listing.id` is populated — for new rows you may need `await session.flush()` before this), add:

```python
        await _upsert_listing_images(session, listing.id, scraped.images or [])
```

Make sure this runs for both the "new listing" and "existing listing update" branches.

- [ ] **Step 4: Manual integration check**

```bash
docker compose restart app
sleep 5

# Trigger a scrape via the running app
docker compose exec -e DISPLAY=:99 app python -c "
import asyncio, logging
logging.basicConfig(level=logging.WARNING)
from sqlalchemy import select
from app.config import settings
from app.database import async_session
from app.models.project import Project
from app.models.listing import Listing
from app.models.listing_image import ListingImage
from app.schemas.scraper import ProjectFilters
from app.scraper.scraper import scrape_project
from app.services.scraper_sync import sync_scraped_listings

async def main():
    async with async_session() as s:
        r = await s.execute(select(Project).where(Project.is_active == True).limit(1))
        p = r.scalar_one()
        filters = ProjectFilters(**p.filters)
        known = {row[0] for row in (await s.execute(
            select(Listing.external_id).where(Listing.project_id == p.id)
        )).all()}
    result = await scrape_project(filters, settings, known_external_ids=known)
    async with async_session() as s:
        await sync_scraped_listings(s, p.id, result.listings, result.complete)
        await s.commit()
        img_count = (await s.execute(
            select(ListingImage).where(ListingImage.image_data.is_(None))
        )).scalars().all()
        print('Newly-inserted unfetched image rows:', len(img_count))
asyncio.run(main())
"
```

Expected: the script prints a non-zero count of unfetched rows after a scrape.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/scraper_sync.py
git commit -m "Upsert listing_image rows during scrape sync"
```

---

## Task 8: Replace `images` URLs in listings API responses

**Files:**
- Modify: `backend/app/api/listings.py` — both list and detail handlers.

- [ ] **Step 1: Add a URL builder helper**

Near the top of `backend/app/api/listings.py` (after the existing imports and helpers):

```python
def _build_image_urls(project_id: UUID, listing_id: UUID, count: int) -> list[str]:
    return [
        f"/api/projects/{project_id}/listings/{listing_id}/image/{i}"
        for i in range(count)
    ]
```

- [ ] **Step 2: Substitute in the list endpoint**

In `list_listings`, after the existing pagination query and before constructing the response, add a batched count query and substitute on each ORM instance:

```python
    from sqlalchemy import func as _func
    listings = result.scalars().all()
    listing_ids = [l.id for l in listings]
    counts = {}
    if listing_ids:
        count_rows = await session.execute(
            _select(ListingImage.listing_id, _func.count())
            .where(ListingImage.listing_id.in_(listing_ids))
            .group_by(ListingImage.listing_id)
        )
        counts = {row[0]: row[1] for row in count_rows.all()}

    for l in listings:
        l.images = _build_image_urls(project_id, l.id, counts.get(l.id, 0))
```

(Match the surrounding code — if `result.scalars().all()` is already in place, just reuse it. Mutating `l.images` in memory is fine for serialization since Pydantic's `from_attributes` reads it; the ORM session isn't dirty-checking JSONB writes here as long as you don't commit. If the existing code commits after this point, do the substitution after the commit.)

- [ ] **Step 3: Substitute in the detail endpoint**

Find the existing `get_listing` (or similarly named) route returning `ListingDetail`. After fetching the `listing` row, query its image count and substitute:

```python
    from sqlalchemy import func as _func
    count_result = await session.execute(
        _select(_func.count()).select_from(ListingImage).where(
            ListingImage.listing_id == listing.id
        )
    )
    count = count_result.scalar_one() or 0
    listing.images = _build_image_urls(project_id, listing.id, count)
```

- [ ] **Step 4: Smoke-test both endpoints**

```bash
docker compose restart app
sleep 5

# List endpoint
curl -s "http://localhost:8000/api/projects/<PROJECT_ID>/listings?per_page=2" \
  -H "Cookie: <auth-cookie>" | python3 -m json.tool | grep images

# Detail endpoint
curl -s "http://localhost:8000/api/projects/<PROJECT_ID>/listings/<LISTING_ID>" \
  -H "Cookie: <auth-cookie>" | python3 -m json.tool | grep images
```

Expected: `images` contains paths like `/api/projects/.../image/0` (no more `img.nepremicnine.net` URLs).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/listings.py
git commit -m "Return backend image URLs in listings responses"
```

---

## Task 9: Frontend verification

No code changes expected — the frontend already treats `listing.images` as `string[]` and renders via `<img src={...}>`. The Vite dev proxy forwards `/api/...` to the backend.

- [ ] **Step 1: Run the dev stack**

```bash
docker compose up -d
```

- [ ] **Step 2: Open a listing in the UI**

Navigate to `http://localhost:5173`, log in, open a project's listings, then open the detail page of a listing that has images.

- [ ] **Step 3: Watch network panel**

Confirm in DevTools that image requests go to `/api/projects/.../image/0..N`, return `200 image/webp`, and render in the gallery.

- [ ] **Step 4: Reload to verify caching**

Reload the page. Confirm the same URLs return quickly (304 or 200 from disk cache) and the database row for that image still shows non-null `image_data`.

```bash
docker compose exec db psql -U postgres -d nepremicnine_tracker -c "
  SELECT listing_id, position, fetched_at, octet_length(image_data) AS bytes
  FROM listing_images
  WHERE image_data IS NOT NULL
  ORDER BY fetched_at DESC
  LIMIT 5;
"
```

Expected: rows with non-NULL `fetched_at` and a reasonable byte count (10–200 KB).

- [ ] **Step 5: Verify ComparisonPage**

If the project has at least two listings, open `ComparisonPage` (search the codebase for the route — likely `/compare` or similar). Confirm `thumbnail_url` (computed `images[0]`) renders correctly.

No commit needed — verification only.
