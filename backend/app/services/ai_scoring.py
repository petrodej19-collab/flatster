import asyncio
import json
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing
from app.models.project import Project
from app.schemas.ai_scoring import AiScoreResult

logger = logging.getLogger(__name__)


@dataclass
class MarketContext:
    avg_price_per_m2: Decimal | None = None
    median_price_per_m2: Decimal | None = None
    min_price_per_m2: Decimal | None = None
    max_price_per_m2: Decimal | None = None
    reference_listings: list[dict] | None = None


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
    description: str | None,
    market: MarketContext | None = None,
) -> str:
    facts = [f"Title: {title}"]
    if location is not None:
        facts.append(f"Location: {location}")
    if price is not None:
        facts.append(f"Price: {price} EUR")
    if price_per_m2 is not None:
        facts.append(f"Price per m2: {price_per_m2} EUR/m2")
    if size_m2 is not None:
        facts.append(f"Size: {size_m2} m2")
    if rooms is not None:
        facts.append(f"Rooms: {rooms}")
    if floor is not None:
        facts.append(f"Floor: {floor}")
    if year_built is not None:
        facts.append(f"Year built: {year_built}")
    if year_renovated is not None:
        facts.append(f"Year renovated: {year_renovated}")
    if energy_class is not None:
        facts.append(f"Energy class: {energy_class}")

    facts_str = "\n".join(facts)

    desc_section = f"\nDescription:\n{description}\n" if description else ""

    # Market context section
    market_section = ""
    if market:
        market_lines = []
        if market.avg_price_per_m2:
            market_lines.append(f"Average price/m2: {market.avg_price_per_m2:.0f} EUR")
        if market.median_price_per_m2:
            market_lines.append(f"Median price/m2: {market.median_price_per_m2:.0f} EUR")
        if market.min_price_per_m2 and market.max_price_per_m2:
            market_lines.append(f"Range: {market.min_price_per_m2:.0f} – {market.max_price_per_m2:.0f} EUR/m2")
        if market_lines:
            market_section = "\nMarket context (same search):\n" + "\n".join(market_lines) + "\n"

    # Reference listings section
    ref_section = ""
    if market and market.reference_listings:
        ref_lines = []
        for ref in market.reference_listings:
            ref_lines.append(f"- Score {ref['score']}: {ref['title']} | {ref['price']}€ | {ref['size']}m2 | {ref['price_m2']}€/m2 | built:{ref.get('year', '?')} | floor:{ref.get('floor', '?')}")
        ref_section = "\nReference listings (already scored, use as calibration):\n" + "\n".join(ref_lines) + "\n"

    return f"""You are a Slovenian real estate expert scoring apartments for a buyer. Your scores MUST be well-distributed — use the full 20-95 range, not just 60-80.

SCORING RUBRIC (follow strictly):
  90-95: Exceptional — below-market price, great location, modern/renovated, block, good floor, all permits OK
  80-89: Very good — competitive price, solid location, good condition, no red flags
  70-79: Good — fair price, decent condition, minor issues only
  60-69: Average — some concerns (older, needs minor work, slightly overpriced, or mediocre location)
  50-59: Below average — multiple issues (overpriced, needs renovation, poor floor, or in a house)
  40-49: Poor — significant problems (very overpriced, major renovation needed, legal issues)
  20-39: Bad — major red flags (missing permits, extreme overpricing, basement + house combo, uninhabitable)

PRICE ADJUSTMENT RULES (adjust the effective price before scoring value):
- Apartment in a house (hiša) instead of a block (blok): treat price as 15% higher. Clues: "stanovanje v hiši", "del hiše", "v stanovanjski hiši", only 1-2 floors, no elevator mentioned, garden/yard.
- Basement or semi-basement (kletno, polkletno, klet, souterrain, floor "K" or "PK"): treat price as 20% higher. Very hard to resell. Always flag in red_flags.
- Built before 1981 and NOT renovated: treat price as 10% higher (earthquake risk, old construction standards, likely needs work).

OTHER SCORING FACTORS:
- Missing "gradbeno dovoljenje" or "uporabno dovoljenje": automatic cap at 40. Major legal risk.
- Needs renovation ("potrebna obnova", "za renoviranje", poor condition): subtract 15-25 points depending on extent.
- Compare price/m2 against the market context below. Significantly above median = overpriced, below = good value.
- Ground floor (pritličje) without garden/terrace: slight penalty (noise, privacy).
- Top floor without elevator: slight penalty for accessibility.
- Good energy class (A, B): bonus. Poor energy class (E, F, G): penalty.

CRITICAL: Each listing is different. Differentiate! Two apartments at similar prices can have very different scores based on location, condition, floor, building type, permits. Do NOT default to the same score.
{market_section}{ref_section}
Property to score:
{facts_str}
{desc_section}
Respond with a JSON object (no markdown, raw JSON only):
{{
  "score": <integer 20-95>,
  "summary": "<2-3 sentence assessment>",
  "investment": {{
    "rating": "<Poor|Fair|Good|Excellent>",
    "points": ["<point 1>", "<point 2>", ...]
  }},
  "livability": {{
    "rating": "<Poor|Fair|Good|Excellent>",
    "points": ["<point 1>", "<point 2>", ...]
  }},
  "red_flags": ["<flag 1>", ...],
  "green_flags": ["<flag 1>", ...]
}}"""


def parse_ai_response(text: str) -> AiScoreResult | None:
    # Strip markdown code fences if present
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        # Remove first line (```json or ```) and last line (```)
        inner_lines = lines[1:]
        if inner_lines and inner_lines[-1].strip() == "```":
            inner_lines = inner_lines[:-1]
        stripped = "\n".join(inner_lines).strip()

    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse AI response as JSON")
        return None

    try:
        # Clamp score to 0-100
        score = data.get("score", 0)
        score = max(0, min(100, int(score)))
        data["score"] = score
        return AiScoreResult(**data)
    except Exception as e:
        logger.warning("Failed to construct AiScoreResult: %s", e)
        return None


async def score_listing(
    client,
    listing: Listing,
    market: MarketContext | None,
    settings,
) -> AiScoreResult | None:
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
        market=market,
    )

    try:
        response = await client.messages.create(
            model=settings.AI_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        return parse_ai_response(text)
    except Exception as e:
        logger.error("AI scoring API error for listing %s: %s", listing.id, e)
        return None


async def score_project_listings_ai(
    session: AsyncSession,
    project_id: UUID,
    settings,
) -> int:
    if not settings.ANTHROPIC_API_KEY:
        logger.info("ANTHROPIC_API_KEY not set, skipping AI scoring")
        return 0

    # Lazy import so it doesn't fail when SDK isn't installed
    import anthropic

    # Check project exists and has AI scoring enabled
    project_result = await session.execute(
        select(Project).where(Project.id == project_id)
    )
    project = project_result.scalar_one_or_none()
    if project is None or not project.ai_scoring_enabled:
        return 0

    # Get unscored listings in active/price_changed status.
    # Description is optional: when missing (e.g., detail page blocked by Cloudflare),
    # the model still scores based on card-level facts (price, size, year, floor, etc.).
    listings_result = await session.execute(
        select(Listing)
        .where(
            Listing.project_id == project_id,
            Listing.ai_score.is_(None),
            Listing.status.in_(["active", "price_changed"]),
        )
        .limit(settings.AI_MAX_LISTINGS_PER_RUN)
    )
    listings = listings_result.scalars().all()

    if not listings:
        return 0

    # Build market context
    active_filter = [
        Listing.project_id == project_id,
        Listing.status.in_(["active", "price_changed"]),
        Listing.price_per_m2.isnot(None),
    ]

    stats_result = await session.execute(
        select(
            func.avg(Listing.price_per_m2),
            func.min(Listing.price_per_m2),
            func.max(Listing.price_per_m2),
        ).where(*active_filter)
    )
    avg_ppm2, min_ppm2, max_ppm2 = stats_result.one()

    # Median via percentile
    median_result = await session.execute(
        select(func.percentile_cont(0.5).within_group(Listing.price_per_m2))
        .where(*active_filter)
    )
    median_ppm2 = median_result.scalar_one_or_none()

    # Reference listings: pick ~5 diverse already-scored listings as calibration anchors
    ref_listings = []
    ref_result = await session.execute(
        select(Listing)
        .where(
            Listing.project_id == project_id,
            Listing.ai_score.isnot(None),
        )
        .order_by(Listing.ai_score.desc())
    )
    scored_all = ref_result.scalars().all()
    if scored_all:
        # Pick top, bottom, and a few spread across the range
        indices = set()
        n = len(scored_all)
        for idx in [0, n // 4, n // 2, 3 * n // 4, n - 1]:
            indices.add(min(idx, n - 1))
        for idx in sorted(indices):
            l = scored_all[idx]
            ref_listings.append({
                "score": int(l.ai_score),
                "title": l.title,
                "price": str(l.price) if l.price else "?",
                "size": str(l.size_m2) if l.size_m2 else "?",
                "price_m2": str(round(l.price_per_m2)) if l.price_per_m2 else "?",
                "year": l.year_built,
                "floor": l.floor,
            })

    market = MarketContext(
        avg_price_per_m2=avg_ppm2,
        median_price_per_m2=median_ppm2,
        min_price_per_m2=min_ppm2,
        max_price_per_m2=max_ppm2,
        reference_listings=ref_listings if ref_listings else None,
    )

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    scored_count = 0
    for i, listing in enumerate(listings):
        if i > 0:
            await asyncio.sleep(settings.AI_SCORING_DELAY)

        result = await score_listing(client, listing, market, settings)
        if result is not None:
            listing.ai_score = Decimal(str(result.score))
            listing.ai_analysis = json.dumps(result.model_dump())
            scored_count += 1

    await session.commit()
    return scored_count
