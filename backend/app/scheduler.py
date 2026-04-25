import logging
from datetime import datetime, timezone
from uuid import UUID

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

_session_factory: async_sessionmaker | None = None


async def init_scheduler(session_factory: async_sessionmaker) -> AsyncIOScheduler:
    global _session_factory
    _session_factory = session_factory

    scheduler = AsyncIOScheduler()

    async with session_factory() as session:
        from app.models.project import Project

        result = await session.execute(
            select(Project).where(Project.is_active == True)  # noqa: E712
        )
        projects = result.scalars().all()

        for project in projects:
            register_project_job(scheduler, project.id)
            logger.info("Registered scrape job for project %s", project.id)

    logger.info("Scheduler initialized with %d active projects", len(projects))
    return scheduler


def register_project_job(scheduler: AsyncIOScheduler, project_id: UUID) -> None:
    job_id = f"scrape_{project_id}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        _run_project_scrape,
        "interval",
        hours=settings.SCHEDULE_INTERVAL_HOURS,
        id=job_id,
        args=[project_id],
        jitter=600,
        replace_existing=True,
    )


def unregister_project_job(scheduler: AsyncIOScheduler, project_id: UUID) -> None:
    job_id = f"scrape_{project_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


async def _run_project_scrape(project_id: UUID) -> None:
    if _session_factory is None:
        logger.error("Session factory not initialized")
        return

    try:
        async with _session_factory() as session:
            from app.models.project import Project
            from app.schemas.scraper import ProjectFilters
            from app.scraper.scraper import scrape_project
            from app.services.scraper_sync import sync_scraped_listings

            result = await session.execute(
                select(Project).where(Project.id == project_id)
            )
            project = result.scalar_one_or_none()
            if project is None:
                logger.warning("Project %s not found, skipping scrape", project_id)
                return

            if not project.is_active:
                logger.info("Project %s is inactive, skipping scrape", project_id)
                return

            filters = ProjectFilters(**project.filters)
            logger.info("Starting scheduled scrape for project %s", project_id)

            # Get known external IDs to skip detail scraping for existing listings
            from app.models.listing import Listing
            existing_result = await session.execute(
                select(Listing.external_id).where(Listing.project_id == project_id)
            )
            known_ids = {row[0] for row in existing_result.all()}

            scrape_result = await scrape_project(filters, settings, known_external_ids=known_ids)

            sync_result = await sync_scraped_listings(
                session, project.id, scrape_result.listings, scrape_result.complete
            )

            project.last_scraped_at = datetime.utcnow()
            await session.commit()

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

            logger.info(
                "Scheduled scrape for project %s complete: %d found, %d new, %d updated, %d sold",
                project_id,
                sync_result.listings_found,
                sync_result.new,
                sync_result.updated,
                sync_result.marked_sold,
            )

    except Exception:
        logger.exception("Scheduled scrape failed for project %s", project_id)
