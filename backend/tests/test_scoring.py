from decimal import Decimal


class TestScorePricePerM2:
    def test_at_average(self):
        from app.services.scoring import _score_price_per_m2
        assert _score_price_per_m2(Decimal("2000"), Decimal("2000")) == Decimal("50")

    def test_half_average(self):
        from app.services.scoring import _score_price_per_m2
        assert _score_price_per_m2(Decimal("1000"), Decimal("2000")) == Decimal("100")

    def test_double_average(self):
        from app.services.scoring import _score_price_per_m2
        assert _score_price_per_m2(Decimal("4000"), Decimal("2000")) == Decimal("0")

    def test_none_returns_neutral(self):
        from app.services.scoring import _score_price_per_m2
        assert _score_price_per_m2(None, Decimal("2000")) == Decimal("50")

    def test_zero_average_returns_neutral(self):
        from app.services.scoring import _score_price_per_m2
        assert _score_price_per_m2(Decimal("2000"), Decimal("0")) == Decimal("50")


class TestScoreYear:
    def test_new_building(self):
        from app.services.scoring import _score_year
        assert _score_year(2024, None) == Decimal("100")

    def test_old_building(self):
        from app.services.scoring import _score_year
        assert _score_year(1940, None) == Decimal("0")

    def test_renovated_takes_precedence(self):
        from app.services.scoring import _score_year
        score_old = _score_year(1960, None)
        score_renovated = _score_year(1960, 2015)
        assert score_renovated > score_old

    def test_none_returns_neutral(self):
        from app.services.scoring import _score_year
        assert _score_year(None, None) == Decimal("50")


class TestScoreSize:
    def test_at_average(self):
        from app.services.scoring import _score_size
        assert _score_size(Decimal("60"), Decimal("60")) == Decimal("50")

    def test_double_average(self):
        from app.services.scoring import _score_size
        assert _score_size(Decimal("120"), Decimal("60")) == Decimal("100")

    def test_none_returns_neutral(self):
        from app.services.scoring import _score_size
        assert _score_size(None, Decimal("60")) == Decimal("50")


class TestScoreEnergyClass:
    def test_a1(self):
        from app.services.scoring import _score_energy_class
        assert _score_energy_class("A1") == Decimal("100")

    def test_d(self):
        from app.services.scoring import _score_energy_class
        assert _score_energy_class("D") == Decimal("40")

    def test_none_returns_neutral(self):
        from app.services.scoring import _score_energy_class
        assert _score_energy_class(None) == Decimal("50")


class TestScoreFloor:
    def test_middle_floor(self):
        from app.services.scoring import _score_floor
        assert _score_floor("2/4") == Decimal("100")

    def test_ground_floor(self):
        from app.services.scoring import _score_floor
        assert _score_floor("pritličje") == Decimal("60")

    def test_top_floor(self):
        from app.services.scoring import _score_floor
        assert _score_floor("4/4") == Decimal("80")

    def test_none_returns_neutral(self):
        from app.services.scoring import _score_floor
        assert _score_floor(None) == Decimal("50")


class TestCalculateScore:
    def test_returns_weighted_sum(self):
        from app.services.scoring import calculate_listing_score
        score = calculate_listing_score(
            price_per_m2=Decimal("2000"),
            avg_price_per_m2=Decimal("2000"),
            year_built=2020,
            year_renovated=None,
            size_m2=Decimal("60"),
            avg_size=Decimal("60"),
            energy_class=None,
            floor=None,
        )
        assert score == Decimal("50.00")

    def test_perfect_listing(self):
        from app.services.scoring import calculate_listing_score
        score = calculate_listing_score(
            price_per_m2=Decimal("1000"),
            avg_price_per_m2=Decimal("2000"),
            year_built=2024,
            year_renovated=None,
            size_m2=Decimal("120"),
            avg_size=Decimal("60"),
            energy_class="A1",
            floor="2/4",
        )
        assert score == Decimal("100.00")
