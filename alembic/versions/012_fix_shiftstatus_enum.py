"""add missing shiftstatus enum values and extend offerStatus

Revision ID: 012_fix_enums
Revises: 011_reset_institutions
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op

revision: str = "012_fix_enums"
down_revision: str = "011_reset_institutions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add missing values to shiftstatus enum
    op.execute("ALTER TYPE shiftstatus ADD VALUE IF NOT EXISTS 'proposing'")
    op.execute("ALTER TYPE shiftstatus ADD VALUE IF NOT EXISTS 'pending_confirmation'")
    op.execute("ALTER TYPE shiftstatus ADD VALUE IF NOT EXISTS 'uncovered'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; downgrade is a no-op
    pass
