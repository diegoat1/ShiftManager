"""Extend shift_templates with min_code_level_id and requires_emergency_vehicle

Revision ID: 016_extend_shift_template
Revises: 015_add_cooperative
Create Date: 2026-03-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016_extend_shift_template"
down_revision: str = "015_add_cooperative"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shift_templates",
        sa.Column("min_code_level_id", sa.Integer(), sa.ForeignKey("code_levels.id"), nullable=True),
    )
    op.add_column(
        "shift_templates",
        sa.Column("requires_emergency_vehicle", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("shift_templates", "requires_emergency_vehicle")
    op.drop_column("shift_templates", "min_code_level_id")
