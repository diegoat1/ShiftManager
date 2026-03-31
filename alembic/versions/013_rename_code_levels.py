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
    op.execute("""
        UPDATE code_levels SET
            code = 'WHITE',
            description = '1 - Bianco (Non urgente)'
        WHERE code = 'WHITE'
    """)
    op.execute("""
        UPDATE code_levels SET
            code = 'GREEN',
            description = '2 - Verde (Urgenza minore)'
        WHERE code = 'GREEN'
    """)
    op.execute("""
        UPDATE code_levels SET
            code = 'BLUE',
            description = '3 - Giallo/Azzurro (Urgente)'
        WHERE code = 'YELLOW'
    """)
    op.execute("""
        UPDATE code_levels SET
            code = 'ORANGE',
            description = '4 - Arancione (Alta urgenza)'
        WHERE code = 'ORANGE'
    """)
    op.execute("""
        UPDATE code_levels SET
            code = 'RED',
            description = '5 - Rosso (Emergenza)'
        WHERE code = 'RED'
    """)


def downgrade() -> None:
    op.execute("UPDATE code_levels SET code = 'YELLOW', description = 'Codice Giallo - Urgent' WHERE code = 'BLUE'")
