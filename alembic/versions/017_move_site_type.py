"""Move site_type from institutions to institution_sites

Revision ID: 017_move_site_type
Revises: 016_extend_shift_template
Create Date: 2026-04-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017_move_site_type"
down_revision: str = "016_extend_shift_template"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("institution_sites", sa.Column("site_type", sa.String(50), nullable=True))
    op.drop_column("institutions", "institution_type")


def downgrade() -> None:
    op.add_column("institutions", sa.Column("institution_type", sa.String(50), nullable=True))
    op.drop_column("institution_sites", "site_type")
