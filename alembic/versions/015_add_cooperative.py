"""Add cooperatives table and cooperative_id FK on institutions

Revision ID: 015_add_cooperative
Revises: 014_add_foreign_doc_types
Create Date: 2026-03-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_add_cooperative"
down_revision: str = "014_add_foreign_doc_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cooperatives",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("partita_iva", sa.String(20), nullable=True, unique=True),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("province", sa.String(2), nullable=True),
        sa.Column("email", sa.String(200), nullable=True),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column(
        "institutions",
        sa.Column("cooperative_id", sa.Uuid(), sa.ForeignKey("cooperatives.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("institutions", "cooperative_id")
    op.drop_table("cooperatives")
