from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

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


class TestClassifyListing:
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
