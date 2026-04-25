import logging
from dataclasses import dataclass

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright
from playwright_stealth import Stealth

from app.config import Settings
from app.scraper.constants import USER_AGENT

logger = logging.getLogger(__name__)


@dataclass
class BrowserSession:
    """Holds Playwright resources for cleanup."""

    playwright: Playwright
    browser: Browser
    context: BrowserContext


async def create_browser_session(settings: Settings) -> BrowserSession:
    """Launch headless Chromium and return a fresh browser session.

    IMPORTANT: nepremicnine.net requires a fresh browser context per session.
    Reusing contexts causes dynamic page elements to not render.

    The caller MUST call close_browser_session() when done.
    """
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=settings.SCRAPER_HEADLESS,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--window-size=1920,1080",
        ],
    )
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1920, "height": 1080},
        locale="sl-SI",
        timezone_id="Europe/Ljubljana",
    )
    # Apply stealth to the entire context — all pages inherit it
    stealth = Stealth(
        navigator_languages_override=("sl", "en-US"),
        navigator_platform_override="Win32",
    )
    await stealth.apply_stealth_async(context)
    logger.info("Browser session created (headless=%s, stealth=on)", settings.SCRAPER_HEADLESS)
    return BrowserSession(playwright=pw, browser=browser, context=context)


async def close_browser_session(session: BrowserSession) -> None:
    """Close all Playwright resources."""
    try:
        await session.context.close()
        await session.browser.close()
        await session.playwright.stop()
        logger.info("Browser session closed")
    except Exception:
        logger.exception("Error closing browser session")
