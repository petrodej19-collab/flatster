import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Listing(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("project_id", "external_id", name="uq_listings_project_external"),
        Index("ix_listings_project_status", "project_id", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), index=True
    )
    project: Mapped["Project"] = relationship("Project", back_populates="listings")
    external_id: Mapped[str] = mapped_column(String(100), index=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255), default=None)
    region: Mapped[str | None] = mapped_column(String(100), default=None)
    property_type: Mapped[str | None] = mapped_column(String(50), default=None)
    transaction_type: Mapped[str | None] = mapped_column(String(20), default=None)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    price_per_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), default=None)
    size_m2: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), default=None)
    rooms: Mapped[str | None] = mapped_column(String(20), default=None)
    year_built: Mapped[int | None] = mapped_column(Integer, default=None)
    year_renovated: Mapped[int | None] = mapped_column(Integer, default=None)
    floor: Mapped[str | None] = mapped_column(String(20), default=None)
    land_size_m2: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), default=None)
    energy_class: Mapped[str | None] = mapped_column(String(10), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    images: Mapped[list] = mapped_column(JSONB, default=list)
    agency: Mapped[str | None] = mapped_column(String(255), default=None)
    basic_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    ai_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), default=None)
    ai_analysis: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(20), default="active")
    price_history: Mapped[list] = mapped_column(JSONB, default=list)
    consecutive_misses: Mapped[int] = mapped_column(Integer, default=0)
    first_seen_at: Mapped[datetime | None] = mapped_column(default=None)
    last_seen_at: Mapped[datetime | None] = mapped_column(default=None)
    marked_sold_at: Mapped[datetime | None] = mapped_column(default=None)
