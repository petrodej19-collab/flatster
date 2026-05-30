import csv
import io
import json
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_session
from app.models.listing import Listing
from app.models.project import Project
from app.models.user import User
from app.schemas.listing import ListingDetail, ListingSummary, PaginatedListings

def _search_tokens(q: str | None) -> list[str]:
    """Split a search query on whitespace and lowercase the tokens.

    Lowercasing here means the SQL only needs to lowercase the column side.
    """
    if not q:
        return []
    return [t.lower() for t in q.split() if t]


router = APIRouter()


async def _verify_project_ownership(
    project_id: UUID,
    user: User,
    session: AsyncSession,
) -> None:
    result = await session.execute(
        select(Project.id).where(Project.id == project_id, Project.user_id == user.id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.get("/{project_id}/listings", response_model=PaginatedListings)
async def list_listings(
    project_id: UUID,
    status_filter: str | None = Query(None, alias="status"),
    min_price: float | None = None,
    max_price: float | None = None,
    min_size: float | None = None,
    max_size: float | None = None,
    sort_by: Literal["price", "size_m2", "basic_score", "ai_score", "first_seen_at", "price_per_m2"] = "first_seen_at",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _verify_project_ownership(project_id, current_user, session)

    query = select(Listing).where(Listing.project_id == project_id)

    if status_filter:
        query = query.where(Listing.status == status_filter)
    if min_price is not None:
        query = query.where(Listing.price >= min_price)
    if max_price is not None:
        query = query.where(Listing.price <= max_price)
    if min_size is not None:
        query = query.where(Listing.size_m2 >= min_size)
    if max_size is not None:
        query = query.where(Listing.size_m2 <= max_size)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar()

    # Sort
    sort_column = getattr(Listing, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc().nulls_last())
    else:
        query = query.order_by(sort_column.asc().nulls_last())

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    listings = result.scalars().all()

    return PaginatedListings(
        items=[ListingSummary.model_validate(l) for l in listings],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{project_id}/listings/export")
async def export_listings(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    await _verify_project_ownership(project_id, current_user, session)

    result = await session.execute(
        select(Listing)
        .where(Listing.project_id == project_id)
        .order_by(Listing.ai_score.desc().nulls_last(), Listing.basic_score.desc().nulls_last())
    )
    listings = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Title", "Location", "Price (EUR)", "Price/m² (EUR)", "Size (m²)",
        "Rooms", "Floor", "Year built", "Year renovated", "Energy class",
        "Status", "Basic score", "AI score", "AI summary",
        "Agency", "URL", "First seen", "Last seen",
    ])
    for l in listings:
        ai_summary = ""
        if l.ai_analysis:
            try:
                ai_summary = json.loads(l.ai_analysis).get("summary", "")
            except (json.JSONDecodeError, AttributeError):
                pass
        writer.writerow([
            l.title, l.location, l.price, l.price_per_m2, l.size_m2,
            l.rooms, l.floor, l.year_built, l.year_renovated, l.energy_class,
            l.status, l.basic_score, l.ai_score, ai_summary,
            l.agency, l.url,
            l.first_seen_at.isoformat() if l.first_seen_at else "",
            l.last_seen_at.isoformat() if l.last_seen_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=listings-{project_id}.csv"},
    )


@router.get("/{project_id}/listings/{listing_id}", response_model=ListingDetail)
async def get_listing(
    project_id: UUID,
    listing_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
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

    return ListingDetail.model_validate(listing)


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

    from app.services.ai_scoring import score_listing

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
