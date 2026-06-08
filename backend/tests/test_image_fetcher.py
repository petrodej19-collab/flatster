from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from PIL import Image

from app.services.image_fetcher import encode_webp, fetch_and_store


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


@pytest.mark.asyncio
async def test_fetch_and_store_marks_tombstone_on_decode_failure(monkeypatch):
    row = _FakeRow("https://example.com/broken.jpg")
    session = MagicMock()
    session.commit = AsyncMock()

    mock_resp = MagicMock(status_code=200, content=b"not-a-real-image")
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
