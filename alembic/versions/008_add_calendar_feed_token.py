"""add calendar_feed_token to doctors

Revision ID: 008_calendar
Revises: 007_source
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008_calendar"
down_revision: str = "007_source"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("doctors", sa.Column("calendar_feed_token", sa.String(64), nullable=True))
    op.create_index("ix_doctors_calendar_feed_token", "doctors", ["calendar_feed_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_doctors_calendar_feed_token", "doctors")
    op.drop_column("doctors", "calendar_feed_token")
