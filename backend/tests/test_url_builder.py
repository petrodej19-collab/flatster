import pytest

from app.schemas.scraper import ProjectFilters
from app.scraper.url_builder import build_scrape_url, build_paginated_url


class TestBuildScrapeUrl:
    def test_basic_url(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="ljubljana-mesto",
            property_type="stanovanje",
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/"

    def test_with_sub_region(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="ljubljana-mesto",
            sub_region="lj-center",
            property_type="stanovanje",
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/lj-center/stanovanje/"

    def test_with_single_room(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="gorenjska",
            property_type="stanovanje",
            rooms=["2-sobno"],
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/gorenjska/stanovanje/2-sobno/"

    def test_with_multiple_rooms(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="gorenjska",
            property_type="stanovanje",
            rooms=["2-sobno", "3-sobno"],
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/gorenjska/stanovanje/2-sobno,3-sobno/"

    def test_with_price_range_both(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="ljubljana-mesto",
            property_type="stanovanje",
            price_from=100000,
            price_to=200000,
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/cena-od-100000-do-200000-eur/"

    def test_with_price_from_only(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="ljubljana-mesto",
            property_type="stanovanje",
            price_from=200000,
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/cena-od-200000-eur/"

    def test_with_price_to_only(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="ljubljana-mesto",
            property_type="stanovanje",
            price_to=200000,
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/cena-do-200000-eur/"

    def test_with_size_range(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="podravska",
            property_type="stanovanje",
            size_from=50,
            size_to=100,
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/podravska/stanovanje/velikost-od-50-do-100-m2/"

    def test_with_year_range(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="podravska",
            property_type="stanovanje",
            year_from=2000,
            year_to=2020,
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/podravska/stanovanje/letnik-od-2000-do-2020/"

    def test_rent_transaction(self):
        filters = ProjectFilters(
            transaction="oddaja",
            region="ljubljana-mesto",
            property_type="stanovanje",
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-oddaja/ljubljana-mesto/stanovanje/"

    def test_house_property_type(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="gorenjska",
            property_type="hisa",
        )
        url = build_scrape_url(filters)
        assert url == "https://www.nepremicnine.net/oglasi-prodaja/gorenjska/hisa/"

    def test_all_filters_combined(self):
        filters = ProjectFilters(
            transaction="prodaja",
            region="ljubljana-mesto",
            sub_region="lj-center",
            property_type="stanovanje",
            rooms=["2-sobno", "25-sobno"],
            price_from=150000,
            price_to=300000,
            size_from=40,
            size_to=80,
            year_from=1990,
            year_to=2020,
        )
        url = build_scrape_url(filters)
        assert url == (
            "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/lj-center/"
            "stanovanje/2-sobno,25-sobno/cena-od-150000-do-300000-eur/"
            "velikost-od-40-do-80-m2/letnik-od-1990-do-2020/"
        )


class TestBuildPaginatedUrl:
    def test_page_1_returns_base_url(self):
        base = "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/"
        assert build_paginated_url(base, 1) == base

    def test_page_2(self):
        base = "https://www.nepremicnine.net/oglasi-prodaja/ljubljana-mesto/stanovanje/"
        assert build_paginated_url(base, 2) == base + "2/"

    def test_page_10(self):
        base = "https://www.nepremicnine.net/oglasi-prodaja/gorenjska/stanovanje/2-sobno/"
        assert build_paginated_url(base, 10) == base + "10/"


class TestProjectFiltersValidation:
    def test_invalid_region(self):
        with pytest.raises(ValueError, match="Invalid region"):
            ProjectFilters(
                transaction="prodaja",
                region="invalid",
                property_type="stanovanje",
            )

    def test_invalid_sub_region(self):
        with pytest.raises(ValueError, match="Invalid sub_region"):
            ProjectFilters(
                transaction="prodaja",
                region="gorenjska",
                sub_region="invalid",
                property_type="stanovanje",
            )

    def test_rooms_on_non_stanovanje(self):
        with pytest.raises(ValueError, match="only valid for"):
            ProjectFilters(
                transaction="prodaja",
                region="gorenjska",
                property_type="hisa",
                rooms=["2-sobno"],
            )

    def test_invalid_room_type(self):
        with pytest.raises(ValueError, match="Invalid room type"):
            ProjectFilters(
                transaction="prodaja",
                region="gorenjska",
                property_type="stanovanje",
                rooms=["invalid"],
            )

    def test_price_from_greater_than_to(self):
        with pytest.raises(ValueError, match="price_to must be >= price_from"):
            ProjectFilters(
                transaction="prodaja",
                region="gorenjska",
                property_type="stanovanje",
                price_from=200000,
                price_to=100000,
            )

    def test_size_from_greater_than_to(self):
        with pytest.raises(ValueError, match="size_to must be >= size_from"):
            ProjectFilters(
                transaction="prodaja",
                region="gorenjska",
                property_type="stanovanje",
                size_from=100,
                size_to=50,
            )

    def test_year_from_greater_than_to(self):
        with pytest.raises(ValueError, match="year_to must be >= year_from"):
            ProjectFilters(
                transaction="prodaja",
                region="gorenjska",
                property_type="stanovanje",
                year_from=2020,
                year_to=2000,
            )
