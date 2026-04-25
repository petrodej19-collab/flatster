from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.scraper import ProjectFilters


class ProjectCreate(BaseModel):
    name: str
    filters: ProjectFilters
    is_active: bool = True
    ai_scoring_enabled: bool = True


class ProjectUpdate(BaseModel):
    name: str | None = None
    filters: ProjectFilters | None = None
    is_active: bool | None = None
    ai_scoring_enabled: bool | None = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    filters: dict
    scrape_url: str
    is_active: bool
    ai_scoring_enabled: bool
    last_scraped_at: datetime | None
    created_at: datetime
    listing_count: int = 0

    model_config = {"from_attributes": True}
