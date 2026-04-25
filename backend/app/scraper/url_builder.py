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
