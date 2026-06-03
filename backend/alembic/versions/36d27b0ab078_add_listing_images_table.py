"""add listing_images table

Revision ID: 36d27b0ab078
Revises: b3a1f2c8e9d4
Create Date: 2026-06-03 06:00:56.340093

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '36d27b0ab078'
down_revision: Union[str, Sequence[str], None] = 'b3a1f2c8e9d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "listing_images",
        sa.Column(
            "listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("image_data", sa.LargeBinary(), nullable=True),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetch_failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("listing_id", "position"),
    )

    op.execute(
        """
        INSERT INTO listing_images (listing_id, position, source_url)
        SELECT l.id, idx - 1, l.images->>(idx - 1)
        FROM listings l
        JOIN LATERAL generate_series(
            1, LEAST(jsonb_array_length(l.images), 3)
        ) AS idx ON TRUE
        WHERE jsonb_array_length(l.images) > 0
        """
    )


def downgrade() -> None:
    op.drop_table("listing_images")
