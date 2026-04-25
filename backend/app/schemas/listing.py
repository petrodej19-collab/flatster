from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, computed_field


class ListingSummary(BaseModel):
    id: UUID
    external_id: str
    url: str
    title: str
    location: str | None
    price: Decimal | None
    price_per_m2: Decimal | None
    size_m2: Decimal | None
    rooms: str | None
    floor: str | None
    year_built: int | None
    status: str
    basic_score: Decimal | None
    ai_score: Decimal | None = None
    first_seen_at: datetime | None
    images: list[str] = []

    @computed_field
    @property
    def thumbnail_url(self) -> str | None:
        return self.images[0] if self.images else None

    model_config = {"from_attributes": True}


class ListingDetail(ListingSummary):
    description: str | None = None
    energy_class: str | None = None
    year_renovated: int | None = None
    land_size_m2: Decimal | None = None
    agency: str | None = None
    ai_score: Decimal | None = None
    ai_analysis: str | None = None
    price_history: list[dict] = []
    consecutive_misses: int = 0
    last_seen_at: datetime | None = None
    marked_sold_at: datetime | None = None
    created_at: datetime | None = None


class PaginatedListings(BaseModel):
    items: list[ListingSummary]
    total: int
    page: int
    per_page: int
