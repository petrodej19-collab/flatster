import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.ai_scoring import AiScoreResult, InvestmentAnalysis, LivabilityAnalysis
from app.services.ai_scoring import build_prompt, parse_ai_response, score_listing


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ai_response_dict(score: int = 75) -> dict:
    return {
        "score": score,
        "summary": "A decent apartment in a good location.",
        "investment": {
            "rating": "Good",
            "points": ["Good price per m2", "New building"],
        },
        "livability": {
            "rating": "Good",
            "points": ["Quiet area", "Close to public transport"],
        },
        "red_flags": ["High floor maintenance fees"],
        "green_flags": ["Recently renovated"],
    }


def _make_listing(**kwargs) -> MagicMock:
    listing = MagicMock()
    listing.id = "test-uuid"
    listing.title = kwargs.get("title", "Apartment in Ljubljana")
    listing.location = kwargs.get("location", "Ljubljana")
    listing.price = kwargs.get("price", Decimal("150000"))
    listing.price_per_m2 = kwargs.get("price_per_m2", Decimal("2500"))
    listing.size_m2 = kwargs.get("size_m2", Decimal("60"))
    listing.rooms = kwargs.get("rooms", "2")
    listing.floor = kwargs.get("floor", "3/5")
    listing.year_built = kwargs.get("year_built", 2010)
    listing.year_renovated = kwargs.get("year_renovated", None)
    listing.energy_class = kwargs.get("energy_class", "B1")
    listing.description = kwargs.get("description", "A nice apartment with balcony.")
    return listing


def _make_settings() -> MagicMock:
    settings = MagicMock()
    settings.AI_MODEL = "claude-haiku-4-5-20251001"
    settings.AI_MAX_LISTINGS_PER_RUN = 50
    settings.AI_SCORING_DELAY = 0.0
    return settings


# ---------------------------------------------------------------------------
# TestBuildPrompt
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_includes_title_and_price(self):
        prompt = build_prompt(
            title="Cozy Studio",
            location="Maribor",
            price=Decimal("80000"),
            price_per_m2=Decimal("2000"),
            size_m2=Decimal("40"),
            rooms="1",
            floor="2/4",
            year_built=2000,
            year_renovated=None,
            energy_class="C",
            description="Small but comfortable.",
            avg_price_per_m2=Decimal("2200"),
        )
        assert "Cozy Studio" in prompt
        assert "80000" in prompt
        assert "2000" in prompt

    def test_handles_missing_optional_fields(self):
        prompt = build_prompt(
            title="Apartment",
            location=None,
            price=None,
            price_per_m2=None,
            size_m2=None,
            rooms=None,
            floor=None,
            year_built=None,
            year_renovated=None,
            energy_class=None,
            description="Some description.",
            avg_price_per_m2=None,
        )
        assert "Apartment" in prompt
        # None fields should not appear as "None" in the prompt
        assert "Location: None" not in prompt
        assert "Price: None" not in prompt
        assert "Energy class: None" not in prompt

    def test_includes_avg_price_context(self):
        prompt = build_prompt(
            title="Apartment",
            location="Ljubljana",
            price=Decimal("200000"),
            price_per_m2=Decimal("3000"),
            size_m2=Decimal("65"),
            rooms="2",
            floor="1/3",
            year_built=2015,
            year_renovated=None,
            energy_class="A2",
            description="Modern apartment.",
            avg_price_per_m2=Decimal("2800"),
        )
        assert "2800" in prompt
        assert "Average price per m2" in prompt


# ---------------------------------------------------------------------------
# TestParseAiResponse
# ---------------------------------------------------------------------------

class TestParseAiResponse:
    def test_valid_json_response(self):
        raw = json.dumps(_make_ai_response_dict(score=80))
        result = parse_ai_response(raw)
        assert result is not None
        assert isinstance(result, AiScoreResult)
        assert result.score == 80
        assert result.summary == "A decent apartment in a good location."

    def test_invalid_json_returns_none(self):
        result = parse_ai_response("this is not json at all")
        assert result is None

    def test_partial_json_returns_none(self):
        # Missing required fields
        partial = json.dumps({"score": 50})
        result = parse_ai_response(partial)
        assert result is None

    def test_json_with_markdown_wrapping(self):
        raw = json.dumps(_make_ai_response_dict(score=65))
        wrapped = f"```json\n{raw}\n```"
        result = parse_ai_response(wrapped)
        assert result is not None
        assert result.score == 65

    def test_score_clamped_to_0_100(self):
        data = _make_ai_response_dict(score=150)
        result = parse_ai_response(json.dumps(data))
        assert result is not None
        assert result.score == 100

    def test_negative_score_clamped(self):
        data = _make_ai_response_dict(score=-10)
        result = parse_ai_response(json.dumps(data))
        assert result is not None
        assert result.score == 0


# ---------------------------------------------------------------------------
# TestScoreListing
# ---------------------------------------------------------------------------

class TestScoreListing:
    @pytest.mark.asyncio
    async def test_returns_result_on_success(self):
        client = MagicMock()
        message = MagicMock()
        message.content = [MagicMock(text=json.dumps(_make_ai_response_dict(score=72)))]
        client.messages.create = AsyncMock(return_value=message)

        listing = _make_listing()
        settings = _make_settings()

        result = await score_listing(client, listing, Decimal("2500"), settings)

        assert result is not None
        assert result.score == 72
        client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_description(self):
        client = MagicMock()
        client.messages.create = AsyncMock()

        listing = _make_listing(description=None)
        settings = _make_settings()

        result = await score_listing(client, listing, Decimal("2500"), settings)

        assert result is None
        client.messages.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_on_api_error(self):
        client = MagicMock()
        client.messages.create = AsyncMock(side_effect=Exception("API error"))

        listing = _make_listing()
        settings = _make_settings()

        result = await score_listing(client, listing, Decimal("2500"), settings)

        assert result is None
