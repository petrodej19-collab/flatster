import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import settings
from app.database import get_session
from app.models.listing import Listing
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.scraper import ProjectFilters
from app.scraper.url_builder import build_scrape_url

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_user_project(
    project_id: UUID,
    user: User,
    session: AsyncSession,
) -> Project:
    result = await session.execute(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: ProjectCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    scrape_url = build_scrape_url(body.filters)
    project = Project(
        user_id=current_user.id,
        name=body.name,
        filters=body.filters.model_dump(),
        scrape_url=scrape_url,
        is_active=body.is_active,
        ai_scoring_enabled=body.ai_scoring_enabled,
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)

    if project.is_active and hasattr(request.app.state, "scheduler"):
        from app.scheduler import register_project_job

        register_project_job(request.app.state.scheduler, project.id)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        filters=project.filters,
        scrape_url=project.scrape_url,
        is_active=project.is_active,
        ai_scoring_enabled=project.ai_scoring_enabled,
        last_scraped_at=project.last_scraped_at,
        created_at=project.created_at,
        listing_count=0,
    )


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Project).where(Project.user_id == current_user.id)
    )
    projects = result.scalars().all()

    if not projects:
        return []

    # Get listing counts in one query
    count_result = await session.execute(
        select(Listing.project_id, func.count(Listing.id))
        .where(Listing.project_id.in_([p.id for p in projects]))
        .group_by(Listing.project_id)
    )
    counts = dict(count_result.all())

    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            filters=p.filters,
            scrape_url=p.scrape_url,
            is_active=p.is_active,
            ai_scoring_enabled=p.ai_scoring_enabled,
            last_scraped_at=p.last_scraped_at,
            created_at=p.created_at,
            listing_count=counts.get(p.id, 0),
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = await _get_user_project(project_id, current_user, session)

    count_result = await session.execute(
        select(func.count(Listing.id)).where(Listing.project_id == project.id)
    )
    listing_count = count_result.scalar() or 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        filters=project.filters,
        scrape_url=project.scrape_url,
        is_active=project.is_active,
        ai_scoring_enabled=project.ai_scoring_enabled,
        last_scraped_at=project.last_scraped_at,
        created_at=project.created_at,
        listing_count=listing_count,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    body: ProjectUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = await _get_user_project(project_id, current_user, session)
    update_data = body.model_dump(exclude_unset=True)

    if "filters" in update_data:
        filters = ProjectFilters(**update_data["filters"])
        project.filters = filters.model_dump()
        project.scrape_url = build_scrape_url(filters)
    if "name" in update_data:
        project.name = update_data["name"]
    if "is_active" in update_data:
        old_active = project.is_active
        project.is_active = update_data["is_active"]
        if hasattr(request.app.state, "scheduler"):
            from app.scheduler import register_project_job, unregister_project_job

            if not old_active and project.is_active:
                register_project_job(request.app.state.scheduler, project.id)
            elif old_active and not project.is_active:
                unregister_project_job(request.app.state.scheduler, project.id)
    if "ai_scoring_enabled" in update_data:
        project.ai_scoring_enabled = update_data["ai_scoring_enabled"]

    await session.commit()
    await session.refresh(project)

    # When AI scoring is turned on, score all unscored listings
    if update_data.get("ai_scoring_enabled") and project.ai_scoring_enabled:
        from app.services.ai_scoring import score_project_listings_ai

        try:
            scored = await score_project_listings_ai(session, project.id, settings)
            while scored > 0:
                scored = await score_project_listings_ai(session, project.id, settings)
        except Exception:
            logger.exception("AI scoring failed after enabling for project %s", project.id)

    count_result = await session.execute(
        select(func.count(Listing.id)).where(Listing.project_id == project.id)
    )
    listing_count = count_result.scalar() or 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        filters=project.filters,
        scrape_url=project.scrape_url,
        is_active=project.is_active,
        ai_scoring_enabled=project.ai_scoring_enabled,
        last_scraped_at=project.last_scraped_at,
        created_at=project.created_at,
        listing_count=listing_count,
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = await _get_user_project(project_id, current_user, session)

    if hasattr(request.app.state, "scheduler"):
        from app.scheduler import unregister_project_job

        unregister_project_job(request.app.state.scheduler, project.id)

    await session.delete(project)
    await session.commit()


@router.post("/{project_id}/scrape")
async def trigger_scrape(
    project_id: UUID,
    full: bool = False,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    project = await _get_user_project(project_id, current_user, session)
    filters = ProjectFilters(**project.filters)

    from datetime import datetime, timezone

    from app.scraper.scraper import scrape_project
    from app.services.scraper_sync import sync_scraped_listings

    known_ids: set[str] | None = None
    if not full:
        # Get known external IDs to skip detail scraping for existing listings
        existing_result = await session.execute(
            select(Listing.external_id).where(Listing.project_id == project.id)
        )
        known_ids = {row[0] for row in existing_result.all()}

    scrape_result = await scrape_project(filters, settings, known_external_ids=known_ids)
    result = await sync_scraped_listings(
        session, project.id, scrape_result.listings, scrape_result.complete
    )

    project.last_scraped_at = datetime.utcnow()

    # AI scoring for new listings
    ai_scored = 0
    if project.ai_scoring_enabled:
        from app.services.ai_scoring import score_project_listings_ai

        ai_scored = await score_project_listings_ai(session, project.id, settings)

    await session.commit()

    return {
        "listings_found": result.listings_found,
        "new": result.new,
        "updated": result.updated,
        "marked_sold": result.marked_sold,
        "ai_scored": ai_scored,
    }
