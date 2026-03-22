"""add shift_offers and notifications tables

Revision ID: 005_offers
Revises: 004_documents
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005_offers"
down_revision: str = "004_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

offerstatus = sa.Enum(
    "proposed", "viewed", "accepted", "rejected", "expired", "cancelled",
    name="offerstatus",
)


def upgrade() -> None:
    offerstatus.create(op.get_bind(), checkfirst=True)

    # Extend shiftstatus enum with new values
    op.execute("ALTER TYPE shiftstatus ADD VALUE IF NOT EXISTS 'proposing'")
    op.execute("ALTER TYPE shiftstatus ADD VALUE IF NOT EXISTS 'pending_confirmation'")
    op.execute("ALTER TYPE shiftstatus ADD VALUE IF NOT EXISTS 'uncovered'")

    op.create_table(
        "shift_offers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("doctor_id", sa.Uuid(), nullable=False),
        sa.Column("status", offerstatus, nullable=False, server_default="proposed"),
        sa.Column("offered_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("response_note", sa.String(500), nullable=True),
        sa.Column("rank_snapshot", sa.Integer(), nullable=True),
        sa.Column("score_snapshot", sa.Integer(), nullable=True),
        sa.Column("proposed_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposed_by"], ["users.id"]),
        sa.UniqueConstraint("shift_id", "doctor_id"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.String(1000), nullable=True),
        sa.Column("channel", sa.String(20), nullable=False, server_default="in_app"),
        sa.Column("status", sa.String(20), nullable=False, server_default="unread"),
        sa.Column("sent_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("related_entity_type", sa.String(50), nullable=True),
        sa.Column("related_entity_id", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notifications_user_status", "notifications", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_notifications_user_status")
    op.drop_table("notifications")
    op.drop_table("shift_offers")
    offerstatus.drop(op.get_bind(), checkfirst=True)
