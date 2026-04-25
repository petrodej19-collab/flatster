# Phase 4: AI Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Claude-powered listing analysis that produces an AI score (0-100) and structured analysis (investment + livability) for each listing with a description.

**Architecture:** New `ai_scoring` service calls Claude Haiku via the Anthropic SDK, parses structured JSON responses, and stores results in existing `ai_score`/`ai_analysis` columns. Scoring hooks into the post-scrape pipeline and is available as a manual trigger. Frontend displays the score and parsed analysis on the listing detail page.

**Tech Stack:** anthropic Python SDK, Claude claude-haiku-4-5-20251001, existing FastAPI + SQLAlchemy + React stack

---

## File Map

### Backend new files

| File | Responsibility |
|---|---|
| `backend/app/schemas/ai_scoring.py` | AiScoreResult Pydantic model |
| `backend/app/services/ai_scoring.py` | Claude API integration, prompt, parsing, batch scoring |
| `backend/tests/test_ai_scoring.py` | Unit tests with mocked Claude responses |

### Backend modifications

| File | Changes |
|---|---|
| `backend/app/config.py` | Add ANTHROPIC_API_KEY, AI_MODEL, AI_MAX_LISTINGS_PER_RUN, AI_SCORING_DELAY |
| `backend/app/api/listings.py` | Add POST score endpoint for single listing |
| `backend/app/api/projects.py` | Call AI scoring after scrape in trigger_scrape |
| `backend/app/scheduler.py` | Call AI scoring after scrape in _run_project_scrape |

### Frontend modifications

| File | Changes |
|---|---|
| `frontend/src/api/listings.ts` | Add useScoreListing mutation, ai_score sort option |
| `frontend/src/features/listings/ListingDetailPage.tsx` | Replace AI placeholder with score + analysis display |
| `frontend/src/features/listings/ListingsTable.tsx` | Add AI score column |

---

### Task 1: Configuration and Schema

**Files:**
- Modify: `backend/app/config.py`
- Create: `backend/app/schemas/ai_scoring.py`

- [ ] **Step 1: Add AI settings to config**

In `backend/app/config.py`, add after the `SOLD_DETECTION_MISSES` line and before the `# CORS` line:

```python
    # AI Scoring
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-haiku-4-5-20251001"
    AI_MAX_LISTINGS_PER_RUN: int = 50
    AI_SCORING_DELAY: float = 0.5
```

- [ ] **Step 2: Create AI scoring schema**

Create `backend/app/schemas/ai_scoring.py`:

```python
from decimal import Decimal

from pydantic import BaseModel


class InvestmentAnalysis(BaseModel):
    rating: str
    points: list[str]


class LivabilityAnalysis(BaseModel):
    rating: str
    points: list[str]


class AiScoreResult(BaseModel):
    score: int
    summary: str
    investment: InvestmentAnalysis
    livability: LivabilityAnalysis
    red_flags: list[str]
    green_flags: list[str]
```

- [ ] **Step 3: Verify import**

Run: `cd /mnt/d/Projects/Flatster/backend && python3 -c "from app.schemas.ai_scoring import AiScoreResult; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
cd /mnt/d/Projects/Flatster
git add backend/app/config.py backend/app/schemas/ai_scoring.py
git commit -m "feat: add AI scoring config and schema"
```

---

### Task 2: AI Scoring Service — Tests

**Files:**
- Create: `backend/tests/test_ai_scoring.py`

- [ ] **Step 1: Write tests for prompt construction and response parsing**

Create `backend/tests/test_ai_scoring.py`:

```python
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.ai_scoring import AiScoreResult
from app.services.ai_scoring import (
    build_prompt,
    parse_ai_response,
    score_listing,
)


VALID_RESPONSE = json.dumps(
    {
        "score": 72,
        "summary": "Well-priced renovated apartment in central Ljubljana.",
        "investment": {
            "rating": "good",
            "points": [
                "Price per m2 below area average",
                "Recent renovation adds value",
            ],
        },
        "livability": {
            "rating": "moderate",
            "points": [
                "Ground floor may have noise concerns",
                "Good energy class reduces costs",
            ],
        },
        "red_flags": ["Ground floor apartment"],
        "green_flags": ["Recently renovated (2022)", "Energy class B"],
    }
)


class TestBuildPrompt:
    def test_includes_title_and_price(self):
        prompt = build_prompt(
            title="2-sobno stanovanje, Ljubljana",
            location="Ljubljana, Bežigrad",
            price=Decimal("185000"),
            price_per_m2=Decimal("3200"),
            size_m2=Decimal("58"),
            rooms="2-sobno",
            floor="2/4",
            year_built=1985,
            year_renovated=2022,
            energy_class="B",
            description="Prodaja renoviranega stanovanja v centru Ljubljane.",
            avg_price_per_m2=Decimal("3500"),
        )
        assert "185000" in prompt or "185,000" in prompt
        assert "3200" in prompt or "3,200" in prompt
        assert "Ljubljana" in prompt
        assert "renoviranega" in prompt

    def test_handles_missing_optional_fields(self):
        prompt = build_prompt(
            title="Stanovanje",
            location=None,
            price=None,
            price_per_m2=None,
            size_m2=None,
            rooms=None,
            floor=None,
            year_built=None,
            year_renovated=None,
            energy_class=None,
            description="Prodaja stanovanja.",
            avg_price_per_m2=None,
        )
        assert "Stanovanje" in prompt
        assert "Prodaja stanovanja." in prompt

    def test_includes_avg_price_context(self):
        prompt = build_prompt(
            title="Test",
            location=None,
            price=None,
            price_per_m2=Decimal("3000"),
            size_m2=None,
            rooms=None,
            floor=None,
            year_built=None,
            year_renovated=None,
            energy_class=None,
            description="Test description.",
            avg_price_per_m2=Decimal("3500"),
        )
        assert "3500" in prompt or "3,500" in prompt


class TestParseAiResponse:
    def test_valid_json_response(self):
        result = parse_ai_response(VALID_RESPONSE)
        assert isinstance(result, AiScoreResult)
        assert result.score == 72
        assert result.summary == "Well-priced renovated apartment in central Ljubljana."
        assert result.investment.rating == "good"
        assert len(result.investment.points) == 2
        assert result.livability.rating == "moderate"
        assert len(result.red_flags) == 1
        assert len(result.green_flags) == 2

    def test_invalid_json_returns_none(self):
        result = parse_ai_response("This is not JSON at all")
        assert result is None

    def test_partial_json_returns_none(self):
        result = parse_ai_response('{"score": 72}')
        assert result is None

    def test_json_with_markdown_wrapping(self):
        wrapped = f"```json\n{VALID_RESPONSE}\n```"
        result = parse_ai_response(wrapped)
        assert isinstance(result, AiScoreResult)
        assert result.score == 72

    def test_score_clamped_to_0_100(self):
        modified = json.loads(VALID_RESPONSE)
        modified["score"] = 150
        result = parse_ai_response(json.dumps(modified))
        assert result is not None
        assert result.score == 100

    def test_negative_score_clamped(self):
        modified = json.loads(VALID_RESPONSE)
        modified["score"] = -10
        result = parse_ai_response(json.dumps(modified))
        assert result is not None
        assert result.score == 0


class TestScoreListing:
    @pytest.mark.asyncio
    async def test_returns_result_on_success(self):
        mock_client = AsyncMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=VALID_RESPONSE)]
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        mock_settings = MagicMock()
        mock_settings.AI_MODEL = "claude-haiku-4-5-20251001"

        mock_listing = MagicMock()
        mock_listing.title = "Test apartment"
        mock_listing.location = "Ljubljana"
        mock_listing.price = Decimal("185000")
        mock_listing.price_per_m2 = Decimal("3200")
        mock_listing.size_m2 = Decimal("58")
        mock_listing.rooms = "2-sobno"
        mock_listing.floor = "2/4"
        mock_listing.year_built = 1985
        mock_listing.year_renovated = 2022
        mock_listing.energy_class = "B"
        mock_listing.description = "Nice apartment for sale."

        result = await score_listing(
            client=mock_client,
            listing=mock_listing,
            avg_price_per_m2=Decimal("3500"),
            settings=mock_settings,
        )

        assert result is not None
        assert result.score == 72
        mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_description(self):
        mock_listing = MagicMock()
        mock_listing.description = None

        result = await score_listing(
            client=AsyncMock(),
            listing=mock_listing,
            avg_price_per_m2=Decimal("3500"),
            settings=MagicMock(),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_api_error(self):
        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        mock_settings = MagicMock()
        mock_settings.AI_MODEL = "claude-haiku-4-5-20251001"

        mock_listing = MagicMock()
        mock_listing.title = "Test"
        mock_listing.location = None
        mock_listing.price = None
        mock_listing.price_per_m2 = None
        mock_listing.size_m2 = None
        mock_listing.rooms = None
        mock_listing.floor = None
        mock_listing.year_built = None
        mock_listing.year_renovated = None
        mock_listing.energy_class = None
        mock_listing.description = "Some description."

        result = await score_listing(
            client=mock_client,
            listing=mock_listing,
            avg_price_per_m2=None,
            settings=mock_settings,
        )

        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /mnt/d/Projects/Flatster/backend && python3 -m pytest tests/test_ai_scoring.py -v 2>&1 | head -30`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.ai_scoring'`

- [ ] **Step 3: Commit test file**

```bash
cd /mnt/d/Projects/Flatster
git add backend/tests/test_ai_scoring.py
git commit -m "test: add AI scoring unit tests"
```

---

### Task 3: AI Scoring Service — Implementation

**Files:**
- Create: `backend/app/services/ai_scoring.py`

- [ ] **Step 1: Install anthropic SDK**

```bash
cd /mnt/d/Projects/Flatster/backend && pip install anthropic
```

Also add `anthropic` to `requirements.txt` if it exists, or note the dependency.

- [ ] **Step 2: Create AI scoring service**

Create `backend/app/services/ai_scoring.py`:

```python
import asyncio
import json
import logging
import re
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models.listing import Listing
from app.models.project import Project
from app.schemas.ai_scoring import AiScoreResult

logger = logging.getLogger(__name__)


def build_prompt(
    title: str,
    location: str | None,
    price: Decimal | None,
    price_per_m2: Decimal | None,
    size_m2: Decimal | None,
    rooms: str | None,
    floor: str | None,
    year_built: int | None,
    year_renovated: int | None,
    energy_class: str | None,
    description: str,
    avg_price_per_m2: Decimal | None,
) -> str:
    facts = [f"Title: {title}"]
    if location:
        facts.append(f"Location: {location}")
    if price is not None:
        facts.append(f"Price: {price} EUR")
    if price_per_m2 is not None:
        facts.append(f"Price per m2: {price_per_m2} EUR/m2")
    if size_m2 is not None:
        facts.append(f"Size: {size_m2} m2")
    if rooms:
        facts.append(f"Rooms: {rooms}")
    if floor:
        facts.append(f"Floor: {floor}")
    if year_built is not None:
        facts.append(f"Year built: {year_built}")
    if year_renovated is not None:
        facts.append(f"Year renovated: {year_renovated}")
    if energy_class:
        facts.append(f"Energy class: {energy_class}")
    if avg_price_per_m2 is not None:
        facts.append(f"Area average price per m2: {avg_price_per_m2} EUR/m2")

    facts_block = "\n".join(facts)

    return f"""Analyze this Slovenian real estate listing for investment potential and livability.

LISTING DATA:
{facts_block}

DESCRIPTION:
{description}

Return ONLY valid JSON with this exact structure:
{{
  "score": <0-100 overall desirability score>,
  "summary": "<1-2 sentence summary>",
  "investment": {{
    "rating": "<excellent|good|moderate|poor>",
    "points": ["<point 1>", "<point 2>", ...]
  }},
  "livability": {{
    "rating": "<excellent|good|moderate|poor>",
    "points": ["<point 1>", "<point 2>", ...]
  }},
  "red_flags": ["<flag 1>", ...],
  "green_flags": ["<flag 1>", ...]
}}

Scoring guidance:
- 80-100: Excellent deal, great location, no red flags
- 60-79: Good value, minor concerns
- 40-59: Average, notable trade-offs
- 0-39: Poor value or significant concerns

Consider: price relative to area average, condition, location, energy efficiency, floor, renovation status, and any issues mentioned in the description."""


def parse_ai_response(text: str) -> AiScoreResult | None:
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse AI response as JSON")
        return None

    # Clamp score to 0-100
    if "score" in data:
        data["score"] = max(0, min(100, int(data["score"])))

    try:
        return AiScoreResult.model_validate(data)
    except Exception:
        logger.warning("AI response JSON does not match expected schema")
        return None


async def score_listing(
    client,
    listing,
    avg_price_per_m2: Decimal | None,
    settings: Settings,
) -> AiScoreResult | None:
    if not listing.description:
        return None

    prompt = build_prompt(
        title=listing.title,
        location=listing.location,
        price=listing.price,
        price_per_m2=listing.price_per_m2,
        size_m2=listing.size_m2,
        rooms=listing.rooms,
        floor=listing.floor,
        year_built=listing.year_built,
        year_renovated=listing.year_renovated,
        energy_class=listing.energy_class,
        description=listing.description,
        avg_price_per_m2=avg_price_per_m2,
    )

    try:
        message = await client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = message.content[0].text
        return parse_ai_response(response_text)
    except Exception:
        logger.exception("AI scoring API call failed for listing %s", getattr(listing, "id", "?"))
        return None


async def score_project_listings_ai(
    session: AsyncSession,
    project_id: UUID,
    settings: Settings,
) -> int:
    """Score unscored listings with AI. Returns count of listings scored."""
    if not settings.ANTHROPIC_API_KEY:
        logger.info("ANTHROPIC_API_KEY not set, skipping AI scoring")
        return 0

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Get project to check ai_scoring_enabled
    result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if project is None or not project.ai_scoring_enabled:
        return 0

    # Get unscored listings with descriptions
    result = await session.execute(
        select(Listing).where(
            Listing.project_id == project_id,
            Listing.status.in_(["active", "price_changed"]),
            Listing.ai_score.is_(None),
            Listing.description.isnot(None),
        ).limit(settings.AI_MAX_LISTINGS_PER_RUN)
    )
    listings = result.scalars().all()

    if not listings:
        return 0

    # Compute average price/m2 for context
    avg_result = await session.execute(
        select(Listing.price_per_m2).where(
            Listing.project_id == project_id,
            Listing.status.in_(["active", "price_changed"]),
            Listing.price_per_m2.isnot(None),
        )
    )
    prices = [row[0] for row in avg_result.all()]
    avg_price_per_m2 = sum(prices) / len(prices) if prices else None

    scored = 0
    for listing in listings:
        ai_result = await score_listing(client, listing, avg_price_per_m2, settings)
        if ai_result is not None:
            listing.ai_score = Decimal(str(ai_result.score))
            listing.ai_analysis = json.dumps(ai_result.model_dump())
            scored += 1

        await asyncio.sleep(settings.AI_SCORING_DELAY)

    await session.commit()
    logger.info("AI scored %d/%d listings for project %s", scored, len(listings), project_id)
    return scored
```

- [ ] **Step 3: Run tests**

Run: `cd /mnt/d/Projects/Flatster/backend && python3 -m pytest tests/test_ai_scoring.py -v`
Expected: All tests pass.

- [ ] **Step 4: Run full test suite**

Run: `cd /mnt/d/Projects/Flatster/backend && python3 -m pytest -v --ignore=tests/test_scraper.py`
Expected: All tests pass (77 existing + new AI tests).

- [ ] **Step 5: Commit**

```bash
cd /mnt/d/Projects/Flatster
git add backend/app/services/ai_scoring.py
git commit -m "feat: add AI scoring service with Claude integration"
```

---

### Task 4: Backend Integration — Score Endpoints and Post-Scrape Hook

**Files:**
- Modify: `backend/app/api/listings.py`
- Modify: `backend/app/api/projects.py`
- Modify: `backend/app/scheduler.py`

- [ ] **Step 1: Add manual score endpoint to listings.py**

In `backend/app/api/listings.py`, add this import at the top:

```python
import json
from decimal import Decimal
```

Add this endpoint after the `get_listing` endpoint:

```python
@router.post("/{project_id}/listings/{listing_id}/score")
async def score_listing_ai(
    project_id: UUID,
    listing_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    from app.config import settings

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI scoring not configured",
        )

    await _verify_project_ownership(project_id, current_user, session)

    result = await session.execute(
        select(Listing).where(
            Listing.id == listing_id,
            Listing.project_id == project_id,
        )
    )
    listing = result.scalar_one_or_none()
    if listing is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    if not listing.description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Listing has no description to analyze",
        )

    import anthropic

    from app.services.ai_scoring import build_prompt, parse_ai_response, score_listing

    # Compute avg price/m2 for this project
    avg_result = await session.execute(
        select(func.avg(Listing.price_per_m2)).where(
            Listing.project_id == project_id,
            Listing.status.in_(["active", "price_changed"]),
            Listing.price_per_m2.isnot(None),
        )
    )
    avg_price_per_m2 = avg_result.scalar()

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    ai_result = await score_listing(client, listing, avg_price_per_m2, settings)

    if ai_result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI scoring failed — invalid response from model",
        )

    listing.ai_score = Decimal(str(ai_result.score))
    listing.ai_analysis = json.dumps(ai_result.model_dump())
    await session.commit()

    return {"ai_score": ai_result.score, "ai_analysis": listing.ai_analysis}
```

- [ ] **Step 2: Add AI scoring to trigger_scrape in projects.py**

In `backend/app/api/projects.py`, in the `trigger_scrape` function, add after the `project.last_scraped_at = datetime.now(timezone.utc)` line and before `await session.commit()`:

```python
    # AI scoring for new listings
    ai_scored = 0
    if project.ai_scoring_enabled:
        from app.services.ai_scoring import score_project_listings_ai

        ai_scored = await score_project_listings_ai(session, project.id, settings)
```

And update the return dict to include `ai_scored`:

```python
    return {
        "listings_found": result.listings_found,
        "new": result.new,
        "updated": result.updated,
        "marked_sold": result.marked_sold,
        "ai_scored": ai_scored,
    }
```

- [ ] **Step 3: Add AI scoring to scheduler**

In `backend/app/scheduler.py`, in the `_run_project_scrape` function, add after the `await session.commit()` line (after `project.last_scraped_at = ...`):

```python
            # AI scoring
            if project.ai_scoring_enabled:
                from app.services.ai_scoring import score_project_listings_ai

                try:
                    ai_scored = await score_project_listings_ai(
                        session, project.id, settings
                    )
                    logger.info(
                        "AI scored %d listings for project %s", ai_scored, project_id
                    )
                except Exception:
                    logger.exception(
                        "AI scoring failed for project %s", project_id
                    )
```

- [ ] **Step 4: Run all tests**

Run: `cd /mnt/d/Projects/Flatster/backend && python3 -m pytest -v --ignore=tests/test_scraper.py`
Expected: All tests pass.

- [ ] **Step 5: Commit**

```bash
cd /mnt/d/Projects/Flatster
git add backend/app/api/listings.py backend/app/api/projects.py backend/app/scheduler.py
git commit -m "feat: integrate AI scoring into scrape pipeline and add manual score endpoint"
```

---

### Task 5: Frontend — AI Score Display on Listing Detail

**Files:**
- Modify: `frontend/src/api/listings.ts`
- Modify: `frontend/src/features/listings/ListingDetailPage.tsx`

- [ ] **Step 1: Add useScoreListing mutation to listings.ts**

In `frontend/src/api/listings.ts`, add the import for `useMutation` and `useQueryClient`:

Change the import line from:
```typescript
import { keepPreviousData, useQuery } from "@tanstack/react-query"
```
to:
```typescript
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
```

Add this hook after `useListing`:

```typescript
export function useScoreListing() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ projectId, listingId }: { projectId: string; listingId: string }) => {
      const res = await api.post<{ ai_score: number; ai_analysis: string }>(
        `/projects/${projectId}/listings/${listingId}/score`
      )
      return res.data
    },
    onSuccess: (_, { projectId, listingId }) => {
      queryClient.invalidateQueries({ queryKey: ["listing", projectId, listingId] })
    },
  })
}
```

Also add `"ai_score"` to the `sort_by` type in `ListingFilters`:

```typescript
  sort_by?: string
```

(This is already a plain `string`, so no change needed — just confirming it supports `"ai_score"`.)

- [ ] **Step 2: Update ListingDetailPage to show AI score and analysis**

Replace the AI score placeholder section in `frontend/src/features/listings/ListingDetailPage.tsx`. Replace lines 60-71 (the score panel `<div>`) with:

Replace the entire score panel div (from `<div className="flex flex-col items-center justify-center rounded-lg border p-4">` to its closing `</div>`):

```tsx
        <div className="flex flex-col items-center justify-center rounded-lg border p-4">
          <span className="text-sm text-muted-foreground">Basic Score</span>
          {listing.basic_score != null ? (
            <span className={`mt-1 rounded-lg px-4 py-2 text-3xl font-bold ${scoreColor(listing.basic_score)}`}>
              {Math.round(listing.basic_score)}
            </span>
          ) : (
            <span className="mt-1 text-2xl text-muted-foreground">—</span>
          )}
          <span className="mt-3 text-sm text-muted-foreground">AI Score</span>
          {listing.ai_score != null ? (
            <span className={`mt-1 rounded-lg px-3 py-1 text-2xl font-bold ${scoreColor(listing.ai_score)}`}>
              {Math.round(listing.ai_score)}
            </span>
          ) : listing.description ? (
            <Button
              variant="outline"
              size="sm"
              className="mt-1"
              disabled={scoreListing.isPending}
              onClick={() => scoreListing.mutate({ projectId: id!, listingId: listingId! })}
            >
              {scoreListing.isPending ? "Scoring..." : "Score with AI"}
            </Button>
          ) : (
            <span className="mt-1 text-sm text-muted-foreground">No description</span>
          )}
        </div>
```

Add the `useScoreListing` import and call at the top of the component:

Add to imports:
```typescript
import { useListing, useScoreListing } from "@/api/listings"
```

Inside the component, add after the `useListing` call:
```typescript
  const scoreListing = useScoreListing()
```

- [ ] **Step 3: Add AI analysis section below the score panel**

After the key facts + score grid (after the closing `</div>` of the `grid grid-cols-3` div), add:

```tsx
      {/* AI Analysis */}
      {listing.ai_analysis && (() => {
        try {
          const analysis = JSON.parse(listing.ai_analysis)
          return (
            <>
              <Separator className="my-6" />
              <h2 className="mb-3 text-lg font-semibold">AI Analysis</h2>
              <p className="mb-4 text-sm">{analysis.summary}</p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="mb-2 text-sm font-medium">
                    Investment: <span className="capitalize">{analysis.investment?.rating}</span>
                  </h3>
                  <ul className="space-y-1 text-sm text-muted-foreground">
                    {analysis.investment?.points?.map((p: string, i: number) => (
                      <li key={i}>+ {p}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="mb-2 text-sm font-medium">
                    Livability: <span className="capitalize">{analysis.livability?.rating}</span>
                  </h3>
                  <ul className="space-y-1 text-sm text-muted-foreground">
                    {analysis.livability?.points?.map((p: string, i: number) => (
                      <li key={i}>+ {p}</li>
                    ))}
                  </ul>
                </div>
              </div>
              {analysis.green_flags?.length > 0 && (
                <div className="mt-4">
                  <h3 className="mb-1 text-sm font-medium text-green-700">Green Flags</h3>
                  <div className="flex flex-wrap gap-2">
                    {analysis.green_flags.map((f: string, i: number) => (
                      <span key={i} className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">{f}</span>
                    ))}
                  </div>
                </div>
              )}
              {analysis.red_flags?.length > 0 && (
                <div className="mt-3">
                  <h3 className="mb-1 text-sm font-medium text-red-700">Red Flags</h3>
                  <div className="flex flex-wrap gap-2">
                    {analysis.red_flags.map((f: string, i: number) => (
                      <span key={i} className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700">{f}</span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )
        } catch {
          return null
        }
      })()}
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd /mnt/d/Projects/Flatster/frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 5: Commit**

```bash
cd /mnt/d/Projects/Flatster
git add frontend/src/api/listings.ts frontend/src/features/listings/ListingDetailPage.tsx
git commit -m "feat: add AI score display and score button on listing detail page"
```

---

### Task 6: Frontend — AI Score Column in Listings Table

**Files:**
- Modify: `frontend/src/features/listings/ListingsTable.tsx`

- [ ] **Step 1: Add AI score column header**

In `frontend/src/features/listings/ListingsTable.tsx`, add a new `<th>` after the existing basic score header (the one with `Score{sortIcon("basic_score")}`):

```tsx
              <th className="cursor-pointer p-2 text-center" onClick={() => handleSort("ai_score")}>
                AI{sortIcon("ai_score")}
              </th>
```

- [ ] **Step 2: Add AI score data cell**

In the table body, add a new `<td>` after the basic score `<td>` (the one ending with the scoreColor span):

```tsx
                <td className="p-2 text-center">
                  {listing.basic_score != null ? (
                    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${scoreColor(listing.basic_score)}`}>
                      {Math.round(listing.basic_score)}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="p-2 text-center">
                  {(listing as any).ai_score != null ? (
                    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${scoreColor((listing as any).ai_score)}`}>
                      {Math.round((listing as any).ai_score)}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
```

Note: `ai_score` is not in the `ListingSummary` type yet. Update the type in `frontend/src/api/listings.ts` to add it. In the `ListingSummary` interface, add after `basic_score`:

```typescript
  ai_score: number | null
```

Then the table cell simplifies to:

```tsx
                <td className="p-2 text-center">
                  {listing.ai_score != null ? (
                    <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${scoreColor(listing.ai_score)}`}>
                      {Math.round(listing.ai_score)}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
```

- [ ] **Step 3: Also add ai_score to the backend ListingSummary schema**

In `backend/app/schemas/listing.py`, the `ListingSummary` class needs `ai_score` added. Add after `basic_score`:

```python
    ai_score: Decimal | None = None
```

- [ ] **Step 4: Verify both TypeScript and Python**

Run: `cd /mnt/d/Projects/Flatster/frontend && npx tsc --noEmit`
Run: `cd /mnt/d/Projects/Flatster/backend && python3 -m pytest -v --ignore=tests/test_scraper.py`
Expected: Both pass.

- [ ] **Step 5: Commit**

```bash
cd /mnt/d/Projects/Flatster
git add frontend/src/features/listings/ListingsTable.tsx frontend/src/api/listings.ts backend/app/schemas/listing.py
git commit -m "feat: add AI score column to listings table"
```

---

### Task 7: Full Build Verification

**Files:** None (verification only)

- [ ] **Step 1: Run TypeScript check**

Run: `cd /mnt/d/Projects/Flatster/frontend && npx tsc --noEmit`
Expected: No errors.

- [ ] **Step 2: Run Vite build**

Run: `cd /mnt/d/Projects/Flatster/frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 3: Run backend tests**

Run: `cd /mnt/d/Projects/Flatster/backend && python3 -m pytest -v --ignore=tests/test_scraper.py`
Expected: All tests pass.

- [ ] **Step 4: Verify anthropic is importable**

Run: `cd /mnt/d/Projects/Flatster/backend && python3 -c "import anthropic; print('OK')"`
Expected: `OK`
