"""add users table and auth fields to doctors

Revision ID: 003_users_auth
Revises: 002_enums
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM

revision: str = "003_users_auth"
down_revision: str = "002_enums"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Use postgresql.ENUM with create_type=False to prevent auto-creation
userrole = ENUM(
    "superadmin", "admin", "coordinatore", "operatore", "medico",
    name="userrole",
    create_type=False,
)

homologationstatus = ENUM(
    "pending", "approved", "suspended", "revoked",
    name="homologationstatus",
    create_type=False,
)


def upgrade() -> None:
    # Create enum types using raw SQL with error handling for idempotency
    # (previous failed migrations may have left orphan enum types)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('superadmin', 'admin', 'coordinatore', 'operatore', 'medico');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE homologationstatus AS ENUM ('pending', 'approved', 'suspended', 'revoked');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", userrole, nullable=False, server_default="medico"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ALTER doctors: add new columns
    op.add_column("doctors", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.add_column("doctors", sa.Column("birth_date", sa.Date(), nullable=True))
    op.add_column("doctors", sa.Column("residence_address", sa.String(500), nullable=True))
    op.add_column("doctors", sa.Column("domicile_city", sa.String(100), nullable=True))
    op.add_column("doctors", sa.Column("homologation_status", homologationstatus, nullable=False, server_default="pending"))
    op.add_column("doctors", sa.Column("ordine_province", sa.String(2), nullable=True))
    op.add_column("doctors", sa.Column("ordine_number", sa.String(20), nullable=True))
    op.add_column("doctors", sa.Column("has_own_vehicle", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("doctors", sa.Column("profile_completion_percent", sa.Integer(), nullable=False, server_default="0"))

    op.create_foreign_key("fk_doctors_user_id", "doctors", "users", ["user_id"], ["id"])
    op.create_unique_constraint("uq_doctors_user_id", "doctors", ["user_id"])


def downgrade() -> None:
    op.drop_constraint("uq_doctors_user_id", "doctors")
    op.drop_constraint("fk_doctors_user_id", "doctors")
    op.drop_column("doctors", "profile_completion_percent")
    op.drop_column("doctors", "has_own_vehicle")
    op.drop_column("doctors", "ordine_number")
    op.drop_column("doctors", "ordine_province")
    op.drop_column("doctors", "homologation_status")
    op.drop_column("doctors", "domicile_city")
    op.drop_column("doctors", "residence_address")
    op.drop_column("doctors", "birth_date")
    op.drop_column("doctors", "user_id")

    op.drop_index("ix_users_email")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS homologationstatus")
    op.execute("DROP TYPE IF EXISTS userrole")
