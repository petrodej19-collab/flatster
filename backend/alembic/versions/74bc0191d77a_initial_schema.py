"""initial schema

Revision ID: 74bc0191d77a
Revises:
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "74bc0191d77a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("filters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("scrape_url", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("ai_scoring_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_scraped_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("external_id", sa.String(100), nullable=False, index=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("property_type", sa.String(50), nullable=True),
        sa.Column("transaction_type", sa.String(20), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_per_m2", sa.Numeric(10, 2), nullable=True),
        sa.Column("size_m2", sa.Numeric(8, 2), nullable=True),
        sa.Column("rooms", sa.String(20), nullable=True),
        sa.Column("year_built", sa.Integer(), nullable=True),
        sa.Column("year_renovated", sa.Integer(), nullable=True),
        sa.Column("floor", sa.String(20), nullable=True),
        sa.Column("land_size_m2", sa.Numeric(10, 2), nullable=True),
        sa.Column("energy_class", sa.String(10), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("images", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("agency", sa.String(255), nullable=True),
        sa.Column("basic_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("ai_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("ai_analysis", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("price_history", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("consecutive_misses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.Column("marked_sold_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project_id", "external_id", name="uq_listings_project_external"),
    )

    op.create_index("ix_listings_project_status", "listings", ["project_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_listings_project_status", table_name="listings")
    op.drop_table("listings")
    op.drop_table("projects")
    op.drop_table("users")
