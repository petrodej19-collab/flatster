"""add ai_score_after to projects

Revision ID: 6094fe17ba28
Revises: 36d27b0ab078
Create Date: 2026-06-17 06:41:48.645899

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6094fe17ba28'
down_revision: Union[str, Sequence[str], None] = '36d27b0ab078'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("ai_score_after", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "ai_score_after")
