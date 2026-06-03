import logging
from datetime import datetime, timezone
from io import BytesIO

import httpx
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


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
