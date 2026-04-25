import re
from decimal import Decimal

from app.scraper.list_parser import ListingCard, parse_list_page


class TestParseListPage:
    def test_returns_cards_and_page_count(self, list_page_html: str):
        cards, total_pages = parse_list_page(list_page_html)
        assert isinstance(cards, list)
        assert len(cards) > 0
        assert total_pages >= 1

    def test_card_has_required_fields(self, list_page_html: str):
        cards, _ = parse_list_page(list_page_html)
        card = cards[0]
        assert isinstance(card, ListingCard)
        assert card.external_id
        assert card.url
        assert card.title

    def test_external_id_is_numeric(self, list_page_html: str):
        cards, _ = parse_list_page(list_page_html)
        for card in cards:
            assert re.match(r"^\d+$", card.external_id), f"external_id should be numeric, got: {card.external_id}"

    def test_price_parsed_as_decimal(self, list_page_html: str):
        cards, _ = parse_list_page(list_page_html)
        cards_with_price = [c for c in cards if c.price is not None]
        assert len(cards_with_price) > 0, "At least one card should have a price"
        for card in cards_with_price:
            assert isinstance(card.price, Decimal)
            assert card.price > 0

    def test_url_is_absolute(self, list_page_html: str):
        cards, _ = parse_list_page(list_page_html)
        for card in cards:
            assert card.url.startswith("https://"), f"URL should be absolute, got: {card.url}"

    def test_thumbnail_url_when_present(self, list_page_html: str):
        cards, _ = parse_list_page(list_page_html)
        cards_with_thumb = [c for c in cards if c.thumbnail_url]
        assert len(cards_with_thumb) > 0
        for card in cards_with_thumb:
            assert "nepremicnine.net" in card.thumbnail_url
