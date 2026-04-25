import logging
import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing

logger = logging.getLogger(__name__)

NEUTRAL = Decimal("50")

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


def _score_price_per_m2(price_per_m2: Decimal | None, avg: Decimal | None) -> Decimal:
    if price_per_m2 is None or avg is None or avg == 0:
        return NEUTRAL
    ratio = price_per_m2 / avg
    if ratio <= 1:
        score = Decimal("50") + Decimal("100") * (Decimal("1") - ratio)
    else:
        score = Decimal("50") * (Decimal("2") - ratio)
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

    if year <= 1940:
        return Decimal("0")
    if year >= 2024:
        return Decimal("100")

    if year <= 2020:
        score = Decimal(str(year - 1940)) / Decimal("80") * Decimal("50")
    else:
        score = Decimal("50") + Decimal(str(year - 2020)) * Decimal("50") / Decimal("4")
    return _clamp(score.quantize(Decimal("1")))


def _score_size(size: Decimal | None, avg: Decimal | None) -> Decimal:
    if size is None or avg is None or avg == 0:
        return NEUTRAL
    ratio = size / avg
    score = Decimal("50") * ratio
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
