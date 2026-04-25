import re

import pytest

from app.config import Settings
from app.schemas.scraper import ProjectFilters, ScrapedListing
from app.scraper.scraper import ScrapeResult, scrape_project

pytestmark = pytest.mark.integration


@pytest.fixture
def integration_settings() -> Settings:
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
    filters = ProjectFilters(
        transaction="prodaja",
        region="zasavska",
        property_type="stanovanje",
    )

    result = await scrape_project(filters, integration_settings)
    assert isinstance(result, ScrapeResult)
    listings = result.listings

    assert len(listings) > 0, "Should find at least one listing in Zasavska"
    for listing in listings:
        assert isinstance(listing, ScrapedListing)
        assert listing.external_id
        assert re.match(r"^\d+$", listing.external_id)
        assert listing.url.startswith("https://")
        assert listing.title


@pytest.mark.asyncio
async def test_scraped_listing_has_price(integration_settings: Settings):
    filters = ProjectFilters(
        transaction="prodaja",
        region="zasavska",
        property_type="stanovanje",
    )

    result = await scrape_project(filters, integration_settings)
    listings_with_price = [l for l in result.listings if l.price is not None]
    assert len(listings_with_price) > 0, "At least one listing should have a price"
    for listing in listings_with_price:
        assert listing.price > 0


@pytest.mark.asyncio
async def test_detail_pages_have_extra_data(integration_settings: Settings):
    filters = ProjectFilters(
        transaction="prodaja",
        region="zasavska",
        property_type="stanovanje",
    )

    result = await scrape_project(filters, integration_settings)
    detailed = result.listings[:3]
    has_extra = any(l.description or len(l.images) > 1 for l in detailed)
    assert has_extra, "At least one detailed listing should have description or multiple images"
