"""Add document types for foreign doctors and cooperative

Revision ID: 014_add_foreign_doc_types
Revises: 013_rename_code_levels
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op

revision: str = "014_add_foreign_doc_types"
down_revision: str = "013_rename_code_levels"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO document_types (code, name, description, validity_months, is_mandatory)
        VALUES
        ('dichiarazione_valore', 'Dichiarazione di Valore', 'Per titoli di studio conseguiti all''estero — richiesta ai medici stranieri', NULL, false),
        ('partita_iva', 'Partita IVA', 'Numero di partita IVA per prestazioni professionali autonome', NULL, false)
        ON CONFLICT (code) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DELETE FROM document_types WHERE code IN ('dichiarazione_valore', 'partita_iva')")
