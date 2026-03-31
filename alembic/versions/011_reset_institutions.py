"""delete all institutions so seed can create the real ones

Revision ID: 011_reset_institutions
Revises: 010_cleanup_demo_data
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op

revision: str = "011_reset_institutions"
down_revision: Union[str, None] = "010_cleanup_demo_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove any test/demo institutions so seed.py can create the real ones.
    # CASCADE removes sites → shifts → assignments/offers/requirements.
    op.execute("DELETE FROM institutions")


def downgrade() -> None:
    pass
