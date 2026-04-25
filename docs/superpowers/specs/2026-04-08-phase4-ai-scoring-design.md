# Phase 4: AI Scoring + Polish — Design Spec

**Project:** NepremicnineTracker
**Date:** 2026-04-08
**Scope:** Claude-powered listing analysis, AI score display in frontend, minor UX polish

---

## 1. Overview

Phase 4 adds AI-powered listing analysis using the Claude API. Each listing with a description gets a structured evaluation covering investment potential and livability, producing an `ai_score` (0-100) and `ai_analysis` (structured text). Scoring runs automatically after scrapes (for projects with `ai_scoring_enabled`) and can be triggered manually per listing. The frontend is updated to display the AI score and analysis. Minor polish improvements are included.

### Phases roadmap

- **Phase 1 (done):** Foundation + Scraper
- **Phase 2 (done):** Backend API
- **Phase 3 (done):** React frontend
- **Phase 4 (this spec):** AI scoring + polish

---

## 2. Tech Stack Additions

- **anthropic** Python SDK — Claude API client
- **Claude claude-haiku-4-5-20251001** — fast, cheap model for structured analysis

---

## 3. AI Scoring Service

### 3.1 Prompt Design

The scoring prompt sends structured listing data and the description to Claude, requesting a JSON response with:

```json
{
  "score": 72,
  "summary": "Well-priced renovated apartment in central Ljubljana with good energy efficiency. Minor concern about ground floor location.",
  "investment": {
    "rating": "good",
    "points": [
      "Price per m2 below area average",
      "Recent renovation adds value",
      "Central location supports rental potential"
    ]
  },
  "livability": {
    "rating": "moderate",
    "points": [
      "Ground floor may have noise/privacy concerns",
      "Good energy class reduces costs",
      "Renovated bathroom and kitchen"
    ]
  },
  "red_flags": [
    "Ground floor apartment"
  ],
  "green_flags": [
    "Recently renovated (2022)",
    "Energy class B"
  ]
}
```

The prompt includes:
- Listing title, location, price, price/m2, size, rooms, floor, year built/renovated, energy class
- Full description text
- Project's average price/m2 (computed from active listings) for relative comparison
- Instruction to return valid JSON only, with the schema above

### 3.2 Score Interpretation

- **score** (0-100): Overall desirability. 80+ = excellent deal, 60-79 = good, 40-59 = average, below 40 = poor value or significant concerns
- **investment.rating**: "excellent", "good", "moderate", "poor"
- **livability.rating**: same scale
- **summary**: 1-2 sentence human-readable summary
- **red_flags** / **green_flags**: extracted from description analysis

### 3.3 Service Implementation

New file `backend/app/services/ai_scoring.py`:

- `async def score_listing(listing: Listing, avg_price_per_m2: Decimal | None, settings: Settings) -> AiScoreResult` — calls Claude API, parses JSON response, returns structured result
- `async def score_project_listings_ai(session: AsyncSession, project_id: UUID, settings: Settings) -> AiScoringResult` — scores all unscored active listings in a project with `ai_scoring_enabled`
- Uses `anthropic.AsyncAnthropic` client
- Retries on transient API errors (rate limit, server error) with exponential backoff
- Skips listings without descriptions (returns None)
- Configurable concurrency: processes listings sequentially with a delay between calls

### 3.4 Data Flow

```
Scrape completes
  → sync_scraped_listings (existing)
  → score_project_listings (existing basic scoring)
  → IF project.ai_scoring_enabled:
      score_project_listings_ai (new)
        → For each unscored listing with description:
            score_listing → Claude API → parse JSON
            → Update listing.ai_score, listing.ai_analysis
```

### 3.5 Cost Control

- Only score listings that have `ai_score IS NULL` and `description IS NOT NULL`
- Haiku is ~$0.001 per listing (short prompt + response)
- Configurable `AI_MAX_LISTINGS_PER_RUN` (default: 50) — caps how many listings get scored per scrape
- `AI_SCORING_DELAY` (default: 0.5s) — delay between API calls

---

## 4. Configuration

New settings in `backend/app/config.py`:

```python
# AI Scoring
ANTHROPIC_API_KEY: str = ""
AI_MODEL: str = "claude-haiku-4-5-20251001"
AI_MAX_LISTINGS_PER_RUN: int = 50
AI_SCORING_DELAY: float = 0.5
```

AI scoring is disabled when `ANTHROPIC_API_KEY` is empty — the service checks this before attempting any API calls.

---

## 5. Backend Changes

### 5.1 New Files

| File | Responsibility |
|---|---|
| `backend/app/services/ai_scoring.py` | Claude API integration, prompt construction, response parsing |
| `backend/app/schemas/ai_scoring.py` | AiScoreResult Pydantic model for the parsed response |
| `backend/tests/test_ai_scoring.py` | Unit tests with mocked Claude responses |

### 5.2 Modified Files

| File | Changes |
|---|---|
| `backend/app/config.py` | Add ANTHROPIC_API_KEY, AI_MODEL, AI_MAX_LISTINGS_PER_RUN, AI_SCORING_DELAY |
| `backend/app/api/projects.py` | Call AI scoring after scrape in `trigger_scrape` endpoint |
| `backend/app/api/listings.py` | Add `POST /{project_id}/listings/{listing_id}/score` endpoint for manual AI scoring |
| `backend/app/scheduler.py` | Call AI scoring after scrape in `_run_project_scrape` |

### 5.3 New Endpoint

**`POST /api/projects/{project_id}/listings/{listing_id}/score`**

Triggers AI scoring for a single listing. Returns the AI score result. Returns 400 if listing has no description. Returns 503 if ANTHROPIC_API_KEY is not configured.

Response:
```json
{
  "ai_score": 72,
  "ai_analysis": "{\"score\":72,\"summary\":\"...\",\"investment\":{...},\"livability\":{...},\"red_flags\":[...],\"green_flags\":[...]}"
}
```

### 5.4 ai_analysis Storage

The `ai_analysis` column stores the full JSON string from Claude's response. The frontend parses it for display. This keeps the backend simple (no migration needed — column already exists as Text) and lets the frontend control presentation.

---

## 6. Frontend Changes

### 6.1 Listing Detail Page — AI Score Section

Replace the "AI Score (Phase 4)" placeholder with:

- AI score as a large colored number (same color scheme as basic_score)
- If `ai_analysis` is present, parse the JSON and display:
  - Summary text
  - Investment rating + bullet points
  - Livability rating + bullet points  
  - Red flags (highlighted in red)
  - Green flags (highlighted in green)
- "Score with AI" button if `ai_score` is null and listing has a description
- Loading state while scoring

### 6.2 Listings Table — AI Score Column

Add `ai_score` column to the listings table (sortable), next to the existing `basic_score` column. Shows colored badge same as basic score.

### 6.3 API Hook Addition

New hook in `frontend/src/api/listings.ts`:
- `useScoreListing(projectId, listingId)` — mutation, calls `POST /api/projects/{id}/listings/{id}/score`, invalidates listing query

### 6.4 Files Changed

| File | Changes |
|---|---|
| `frontend/src/features/listings/ListingDetailPage.tsx` | Replace AI placeholder with real score + analysis display, add "Score with AI" button |
| `frontend/src/features/listings/ListingsTable.tsx` | Add AI score column |
| `frontend/src/api/listings.ts` | Add `useScoreListing` mutation hook, add `sort_by` option for `ai_score` |

---

## 7. Testing Strategy

### 7.1 Unit Tests (backend)

- **Prompt construction**: verify listing data is correctly formatted in the prompt
- **Response parsing**: valid JSON → correct AiScoreResult fields, invalid JSON → graceful fallback
- **Missing data handling**: listing without description → skipped, listing without price → still scored
- **API error handling**: mock 429/500 responses → retries, eventual failure → listing skipped
- **Cost control**: verify AI_MAX_LISTINGS_PER_RUN cap is respected

All tests use mocked Claude API responses (no real API calls).

### 7.2 Key Test File

- `backend/tests/test_ai_scoring.py`

---

## 8. Out of Scope

- Batch re-scoring of already-scored listings (users can re-score individually)
- Custom prompts per project
- Alternative AI providers
- Caching or embedding-based similarity search
- AI score in comparison page (shows basic_score only, ai_score visible on detail)
- Frontend tests for AI scoring UI
