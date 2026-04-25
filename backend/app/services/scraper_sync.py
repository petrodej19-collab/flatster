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
    now = datetime.utcnow()
    today = date.today().isoformat()

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
            # Only update images if new data has more (avoid overwriting detail images with card thumbnail)
            if item.images and len(item.images) > len(existing.images or []):
                existing.images = item.images
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
            existing.description = item.description or existing.description
            # Only update images if new data has more (avoid overwriting detail images with card thumbnail)
            if item.images and len(item.images) > len(existing.images or []):
                existing.images = item.images
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

    # Trigger scoring (lazy import since scoring.py may not exist yet)
    from app.services.scoring import score_project_listings

    await score_project_listings(session, project_id)

    return SyncResult(
        listings_found=len(scraped),
        new=new_count,
        updated=updated_count,
        marked_sold=marked_sold,
    )
