"""add native enum types for PostgreSQL

Revision ID: 002_enums
Revises: 001_initial
Create Date: 2026-03-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002_enums"
down_revision: str = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum definitions matching app/utils/enums.py
shiftstatus = sa.Enum(
    "draft", "open", "partially_filled", "filled", "in_progress", "completed", "cancelled",
    name="shiftstatus",
)
assignmentstatus = sa.Enum(
    "proposed", "confirmed", "rejected", "cancelled", "completed",
    name="assignmentstatus",
)
availabilitytype = sa.Enum(
    "available", "preferred", "reluctant",
    name="availabilitytype",
)
unavailabilityreason = sa.Enum(
    "vacation", "sick_leave", "personal", "training", "other",
    name="unavailabilityreason",
)


def upgrade() -> None:
    # Create enum types
    shiftstatus.create(op.get_bind(), checkfirst=True)
    assignmentstatus.create(op.get_bind(), checkfirst=True)
    availabilitytype.create(op.get_bind(), checkfirst=True)
    unavailabilityreason.create(op.get_bind(), checkfirst=True)

    # Convert columns from VARCHAR to native ENUM
    op.execute("ALTER TABLE shifts ALTER COLUMN status TYPE shiftstatus USING status::shiftstatus")
    op.execute("ALTER TABLE shift_assignments ALTER COLUMN status TYPE assignmentstatus USING status::assignmentstatus")
    op.execute("ALTER TABLE doctor_availabilities ALTER COLUMN availability_type TYPE availabilitytype USING availability_type::availabilitytype")
    op.execute("ALTER TABLE doctor_unavailabilities ALTER COLUMN reason TYPE unavailabilityreason USING reason::unavailabilityreason")


def downgrade() -> None:
    op.execute("ALTER TABLE shifts ALTER COLUMN status TYPE VARCHAR(50)")
    op.execute("ALTER TABLE shift_assignments ALTER COLUMN status TYPE VARCHAR(50)")
    op.execute("ALTER TABLE doctor_availabilities ALTER COLUMN availability_type TYPE VARCHAR(50)")
    op.execute("ALTER TABLE doctor_unavailabilities ALTER COLUMN reason TYPE VARCHAR(50)")

    shiftstatus.drop(op.get_bind(), checkfirst=True)
    assignmentstatus.drop(op.get_bind(), checkfirst=True)
    availabilitytype.drop(op.get_bind(), checkfirst=True)
    unavailabilityreason.drop(op.get_bind(), checkfirst=True)
