"""add document_types and documents tables

Revision ID: 004_documents
Revises: 003_users_auth
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_documents"
down_revision: str = "003_users_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

verificationstatus = sa.Enum(
    "pending", "approved", "rejected", "expired",
    name="verificationstatus",
)


def upgrade() -> None:
    verificationstatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "document_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("validity_months", sa.Integer(), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("doctor_id", sa.Uuid(), nullable=False),
        sa.Column("document_type_id", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("verification_status", verificationstatus, nullable=False, server_default="pending"),
        sa.Column("verified_by", sa.Uuid(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_types.id"]),
        sa.ForeignKeyConstraint(["verified_by"], ["users.id"]),
    )

    # Seed mandatory document types
    op.execute("""
        INSERT INTO document_types (code, name, description, validity_months, is_mandatory) VALUES
        ('assicurazione', 'Assicurazione Professionale', 'Polizza RC professionale', 12, true),
        ('laurea', 'Laurea in Medicina', 'Diploma di laurea', NULL, true),
        ('abilitazione', 'Abilitazione Professionale', 'Certificato abilitazione', NULL, true),
        ('iscrizione_ordine', 'Iscrizione Ordine dei Medici', 'Certificato iscrizione ordine', 12, true),
        ('documento_identita', 'Documento di Identità', 'Carta identità o passaporto', 120, true),
        ('codice_fiscale', 'Codice Fiscale', 'Tessera sanitaria/codice fiscale', NULL, false),
        ('cv', 'Curriculum Vitae', 'CV aggiornato', NULL, false),
        ('attestato_bls', 'Attestato BLS-D', 'Basic Life Support Defibrillation', 24, false),
        ('attestato_acls', 'Attestato ACLS', 'Advanced Cardiovascular Life Support', 24, false)
    """)


def downgrade() -> None:
    op.drop_table("documents")
    op.drop_table("document_types")
    verificationstatus.drop(op.get_bind(), checkfirst=True)
