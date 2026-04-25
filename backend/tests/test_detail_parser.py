from decimal import Decimal

from app.scraper.detail_parser import ListingDetail, parse_detail_page


class TestParseDetailPage:
    def test_returns_listing_detail(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert isinstance(detail, ListingDetail)

    def test_title(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert detail.title == "BRDCE, 62.52 m2 - prodaja, stanovanje, 3-sobno"

    def test_description_starts_with(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert detail.description is not None
        assert detail.description.startswith("V mirnem okolju kraja Brdce")

    def test_images(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert len(detail.images) == 26
        assert detail.images[0] == "https://img.nepremicnine.net/slonep_oglasi2/21718551.jpg"

    def test_images_are_deduplicated(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert len(detail.images) == len(set(detail.images))

    def test_size_parsed(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert detail.size_m2 == Decimal("62.52")

    def test_floor_parsed(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert detail.floor == "2/2"

    def test_year_built(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert detail.year_built == 1939

    def test_year_renovated(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert detail.year_renovated == 2020

    def test_location(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert detail.location == "BRDCE"

    def test_bedrooms_and_bathrooms(self, detail_page_html: str):
        detail = parse_detail_page(detail_page_html)
        assert detail.num_bedrooms == 2
        assert detail.num_bathrooms == 1
