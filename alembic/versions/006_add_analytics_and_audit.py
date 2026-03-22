"""add doctor_reliability_stats and audit_logs tables

Revision ID: 006_analytics
Revises: 005_offers
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_analytics"
down_revision: str = "005_offers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "doctor_reliability_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doctor_id", sa.Uuid(), nullable=False),
        sa.Column("total_offers_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_offers_accepted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_offers_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_offers_expired", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cancellations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_response_time_minutes", sa.Float(), nullable=False, server_default="0"),
        sa.Column("acceptance_rate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reliability_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("last_calculated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("doctor_id"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(50), nullable=False),
        sa.Column("old_values", sa.String(5000), nullable=True),
        sa.Column("new_values", sa.String(5000), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_created", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created")
    op.drop_index("ix_audit_logs_entity")
    op.drop_table("audit_logs")
    op.drop_table("doctor_reliability_stats")
