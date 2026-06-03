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
