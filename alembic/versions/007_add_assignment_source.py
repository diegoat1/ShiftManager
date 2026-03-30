"""add source column to shift_assignments

Revision ID: 007_source
Revises: 006_analytics
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_source"
down_revision: str = "006_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shift_assignments", sa.Column("source", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("shift_assignments", "source")
