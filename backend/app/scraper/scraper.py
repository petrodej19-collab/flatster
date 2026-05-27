import asyncio
import logging
import random
from dataclasses import dataclass, field
from decimal import Decimal

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from app.config import Settings
from app.schemas.scraper import ProjectFilters, ScrapedListing
from app.scraper.browser import BrowserSession, close_browser_session, create_browser_session
from app.scraper.detail_parser import ListingDetail, parse_detail_page
from app.scraper.list_parser import ListingCard, parse_list_page
from app.scraper.url_builder import build_paginated_url, build_scrape_url

logger = logging.getLogger(__name__)


class RateLimitedError(Exception):
    """Raised when the scraper gets a 403/429 response."""
    pass


@dataclass
class ScrapeResult:
    listings: list[ScrapedListing] = field(default_factory=list)
    complete: bool = False


async def scrape_project(
    filters: ProjectFilters, settings: Settings, known_external_ids: set[str] | None = None
) -> ScrapeResult:
    """Full scrape pipeline for a project's filters."""
    base_url = build_scrape_url(filters)
    logger.info("Starting scrape for URL: %s", base_url)

    session = await create_browser_session(settings)
    listings: list[ScrapedListing] = []
    try:
        page = await session.context.new_page()

        all_cards, all_pages_fetched = await _scrape_list_pages(session, base_url, settings, page)
        logger.info("Collected %d listing cards (all pages: %s)", len(all_cards), all_pages_fetched)

        if not all_cards:
            return ScrapeResult(listings=[], complete=False)

        await page.close()

        # Split into new vs existing — only scrape details for new listings
        if known_external_ids:
            new_cards = [c for c in all_cards if c.external_id not in known_external_ids]
            existing_cards = [c for c in all_cards if c.external_id in known_external_ids]
            logger.info("Cards: %d new, %d existing (skipping detail scrape for existing)", len(new_cards), len(existing_cards))
        else:
            new_cards = all_cards
            existing_cards = []

        # Scrape details only for new listings
        if new_cards:
            new_listings = await _scrape_detail_pages(session, new_cards, settings)
        else:
            new_listings = []

        # Convert existing cards to listings with card-level data only
        existing_listings = [_card_to_listing(c) for c in existing_cards]

        listings = new_listings + existing_listings
        logger.info("Completed scrape: %d listings (%d with details, %d card-only)", len(listings), len(new_listings), len(existing_listings))

        return ScrapeResult(listings=listings, complete=all_pages_fetched)
    except RateLimitedError:
        logger.error("Scrape aborted due to rate limiting. Returning %d listings collected so far.", len(listings))
        return ScrapeResult(listings=listings, complete=False)
    finally:
        await close_browser_session(session)


async def _scrape_list_pages(
    session: BrowserSession, base_url: str, settings: Settings, page: Page
) -> tuple[list[ListingCard], bool]:
    """Scrape all list pages using the provided page. Returns (cards, all_pages_fetched).

    If pagination is interrupted by a Cloudflare/rate-limit block after page 1, we keep
    the cards collected so far and return all_pages_fetched=False so the sync layer
    treats this as a partial scrape (no sold-marking).
    """
    all_cards: list[ListingCard] = []

    html = await _navigate_with_retry(page, base_url, settings)
    if html is None:
        return [], False

    cards, total_pages = parse_list_page(html)
    all_cards.extend(cards)
    logger.info("Page 1/%d: %d cards", total_pages, len(cards))

    pages_fetched = 1
    for page_num in range(2, total_pages + 1):
        delay = random.uniform(settings.SCRAPER_PAGE_DELAY_MIN, settings.SCRAPER_PAGE_DELAY_MAX)
        await asyncio.sleep(delay)

        page_url = build_paginated_url(base_url, page_num)
        try:
            html = await _navigate_with_retry(page, page_url, settings)
        except RateLimitedError:
            logger.warning(
                "Rate-limited at page %d/%d, keeping %d cards from earlier pages",
                page_num, total_pages, len(all_cards),
            )
            return all_cards, False
        if html is None:
            logger.warning("Failed to load page %d, stopping pagination", page_num)
            break

        cards, _ = parse_list_page(html)
        all_cards.extend(cards)
        pages_fetched += 1
        logger.info("Page %d/%d: %d cards", page_num, total_pages, len(cards))

    return all_cards, pages_fetched == total_pages


async def _scrape_detail_pages(
    session: BrowserSession,
    cards: list[ListingCard],
    settings: Settings,
) -> list[ScrapedListing]:
    """Visit detail pages and merge data with card data."""
    page = await session.context.new_page()
    listings: list[ScrapedListing] = []
    max_details = settings.SCRAPER_MAX_DETAIL_PAGES_PER_RUN

    try:
        for i, card in enumerate(cards):
            if i >= max_details:
                logger.info("Reached detail page limit (%d), remaining cards will have card-level data only", max_details)
                for remaining_card in cards[i:]:
                    listings.append(_card_to_listing(remaining_card))
                break

            if i > 0:
                delay = random.uniform(settings.SCRAPER_DETAIL_DELAY_MIN, settings.SCRAPER_DETAIL_DELAY_MAX)
                await asyncio.sleep(delay)

            try:
                html = await _navigate_with_retry(page, card.url, settings)
            except RateLimitedError:
                logger.warning(
                    "Rate-limited at detail page %d/%d; falling back to card-only data for remaining %d listings",
                    i + 1, len(cards), len(cards) - i,
                )
                for remaining_card in cards[i:]:
                    listings.append(_card_to_listing(remaining_card))
                break

            if html is None:
                logger.warning("Failed to load detail page for %s, using card data only", card.external_id)
                listings.append(_card_to_listing(card))
                continue

            detail = parse_detail_page(html)
            listings.append(_merge_card_and_detail(card, detail))

            if (i + 1) % 5 == 0 or i == 0:
                logger.info("Detail pages: %d/%d completed", i + 1, min(len(cards), max_details))
    finally:
        await page.close()

    return listings


def _is_cloudflare_challenge(title: str, html: str = "") -> bool:
    """Detect Cloudflare challenge page by title or content."""
    cf_titles = ["just a moment", "počakajte trenutek", "un moment"]
    title_lower = title.lower()
    if any(t in title_lower for t in cf_titles):
        return True
    if "challenge-platform" in html or "/cdn-cgi/challenge-platform" in html:
        return True
    return False


async def _wait_for_cloudflare(page: Page, timeout_ms: int = 30000) -> bool:
    """Wait for Cloudflare challenge to resolve. Returns True if resolved."""
    logger.info("Cloudflare challenge detected, waiting for resolution...")
    try:
        # Wait until the challenge script is gone from the page
        await page.wait_for_function(
            """() => {
                const title = document.title.toLowerCase();
                const isCF = title.includes('just a moment')
                    || title.includes('počakajte trenutek')
                    || title.includes('un moment')
                    || document.querySelector('script[src*="challenge-platform"]') !== null;
                return !isCF;
            }""",
            timeout=timeout_ms,
        )
        # Give the page time to fully load after challenge
        await page.wait_for_timeout(3000)
        logger.info("Cloudflare challenge resolved, now at: %s (title: %s)", page.url, await page.title())
        return True
    except PlaywrightTimeout:
        logger.error("Cloudflare challenge did not resolve within %dms", timeout_ms)
        return False


async def _navigate_with_retry(
    page: Page, url: str, settings: Settings
) -> str | None:
    """Navigate to URL with retry logic. Returns page HTML or None on failure."""
    for attempt in range(settings.SCRAPER_MAX_RETRIES):
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=settings.SCRAPER_PAGE_TIMEOUT_MS)
            status = response.status if response else None

            # Detect Cloudflare challenge (403 with challenge page title)
            if status == 403:
                title = await page.title()
                body = await page.content()
                if _is_cloudflare_challenge(title, body):
                    resolved = await _wait_for_cloudflare(page)
                    if resolved:
                        # Challenge passed — now read the actual page
                        try:
                            await page.wait_for_selector(".property-box", timeout=10000)
                        except PlaywrightTimeout:
                            pass
                        await page.wait_for_timeout(1000)
                        return await page.content()
                    else:
                        logger.error("Cloudflare challenge failed — stopping scrape")
                        raise RateLimitedError("Cloudflare challenge timeout")

                # Real 403 (not Cloudflare)
                logger.error("Hard 403 block (not Cloudflare) for %s", url)
                raise RateLimitedError(f"HTTP {status}")

            if status == 429:
                logger.error("Rate limited (HTTP 429) — stopping scrape")
                raise RateLimitedError(f"HTTP {status}")

            if status and status >= 400:
                logger.warning("HTTP %d for %s", status, url)
                if attempt < settings.SCRAPER_MAX_RETRIES - 1:
                    backoff = 2 ** (attempt + 1)
                    await asyncio.sleep(backoff)
                continue

            # Wait for listing content to render
            try:
                await page.wait_for_selector(".property-box", timeout=10000)
            except PlaywrightTimeout:
                pass  # Page may legitimately have no results
            await page.wait_for_timeout(1000)
            html = await page.content()
            return html
        except RateLimitedError:
            raise
        except PlaywrightTimeout:
            logger.warning("Timeout loading %s (attempt %d/%d)", url, attempt + 1, settings.SCRAPER_MAX_RETRIES)
        except Exception:
            logger.exception("Error loading %s (attempt %d/%d)", url, attempt + 1, settings.SCRAPER_MAX_RETRIES)

        if attempt < settings.SCRAPER_MAX_RETRIES - 1:
            backoff = 2 ** (attempt + 1)
            await asyncio.sleep(backoff)

    return None


def _card_to_listing(card: ListingCard) -> ScrapedListing:
    """Convert a ListingCard (list page data only) to a ScrapedListing."""
    price_per_m2 = None
    if card.price and card.size_m2 and card.size_m2 > 0:
        price_per_m2 = (card.price / card.size_m2).quantize(Decimal("0.01"))

    return ScrapedListing(
        external_id=card.external_id,
        url=card.url,
        title=card.title,
        price=card.price,
        price_per_m2=price_per_m2,
        size_m2=card.size_m2,
        rooms=card.rooms,
        year_built=card.year_built,
        floor=card.floor,
        property_type=card.property_type,
        transaction_type=card.transaction_type,
        agency=card.agency,
        images=[card.thumbnail_url] if card.thumbnail_url else [],
    )


def _merge_card_and_detail(card: ListingCard, detail: ListingDetail) -> ScrapedListing:
    """Merge card-level data with detail page data. Detail data takes precedence where available."""
    size = detail.size_m2 if detail.size_m2 is not None else card.size_m2
    price_per_m2 = None
    if card.price and size and size > 0:
        price_per_m2 = (card.price / size).quantize(Decimal("0.01"))

    return ScrapedListing(
        external_id=card.external_id,
        url=card.url,
        title=detail.title or card.title,
        location=detail.location,
        property_type=card.property_type,
        transaction_type=card.transaction_type,
        price=card.price,
        price_per_m2=price_per_m2,
        size_m2=size,
        rooms=card.rooms,
        year_built=detail.year_built or card.year_built,
        year_renovated=detail.year_renovated,
        floor=detail.floor or card.floor,
        land_size_m2=detail.land_size_m2,
        energy_class=detail.energy_class,
        description=detail.description,
        images=detail.images if detail.images else ([card.thumbnail_url] if card.thumbnail_url else []),
        agency=card.agency,
    )
