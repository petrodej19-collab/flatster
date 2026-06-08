from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.listings import apply_image_urls
from app.database import get_session
from app.models.favorite import Favorite
from app.models.listing import Listing
from app.models.user import User
from app.schemas.listing import ListingSummary

router = APIRouter()


@router.post("/{listing_id}", status_code=201)
async def add_favorite(
    listing_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    # Check listing exists
    result = await session.execute(select(Listing).where(Listing.id == listing_id))
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

    fav = Favorite(user_id=current_user.id, listing_id=listing_id)
    session.add(fav)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already favorited")
    return {"status": "favorited"}


@router.delete("/{listing_id}", status_code=204)
async def remove_favorite(
    listing_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.listing_id == listing_id,
        )
    )
    fav = result.scalar_one_or_none()
    if fav is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not favorited")

    await session.delete(fav)
    await session.commit()


@router.get("", response_model=list[ListingSummary])
async def list_favorites(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(Listing)
        .join(Favorite, Favorite.listing_id == Listing.id)
        .where(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
    )
    listings = result.scalars().all()
    await apply_image_urls(session, listings)
    return [ListingSummary.model_validate(l) for l in listings]
