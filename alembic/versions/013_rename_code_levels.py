"""Rename code levels: add numbers and rename YELLOW to BLUE

Revision ID: 013_rename_code_levels
Revises: 012_fix_enums
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op

revision: str = "013_rename_code_levels"
down_revision: str = "012_fix_enums"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # If a BLUE row already exists and YELLOW also exists, remove the stale BLUE
    # so we can rename YELLOW → BLUE without a unique constraint violation.
    op.execute("""
        DELETE FROM code_levels
        WHERE code = 'BLUE'
          AND EXISTS (SELECT 1 FROM code_levels WHERE code = 'YELLOW')
    """)
    # Rename YELLOW → BLUE (no-op if YELLOW was already renamed in a prior run)
    op.execute("""
        UPDATE code_levels SET
            code = 'BLUE',
            description = '3 - Giallo/Azzurro (Urgente)'
        WHERE code = 'YELLOW'
    """)
    # Update descriptions for the remaining codes (idempotent)
    op.execute("UPDATE code_levels SET description = '1 - Bianco (Non urgente)' WHERE code = 'WHITE'")
    op.execute("UPDATE code_levels SET description = '2 - Verde (Urgenza minore)' WHERE code = 'GREEN'")
    op.execute("UPDATE code_levels SET description = '3 - Giallo/Azzurro (Urgente)' WHERE code = 'BLUE'")
    op.execute("UPDATE code_levels SET description = '4 - Arancione (Alta urgenza)' WHERE code = 'ORANGE'")
    op.execute("UPDATE code_levels SET description = '5 - Rosso (Emergenza)' WHERE code = 'RED'")


def downgrade() -> None:
    op.execute("UPDATE code_levels SET code = 'YELLOW', description = 'Codice Giallo - Urgent' WHERE code = 'BLUE'")
