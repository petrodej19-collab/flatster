import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ListingImage(Base):
    __tablename__ = "listing_images"

    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("listings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    image_data: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    mime_type: Mapped[str | None] = mapped_column(Text, default=None)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    fetch_failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
