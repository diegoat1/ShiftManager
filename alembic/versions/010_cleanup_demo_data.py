"""remove all demo data, keep only admin and reference data

Revision ID: 010_cleanup_demo_data
Revises: 009_messages
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op

revision: str = "010_cleanup_demo_data"
down_revision: Union[str, None] = "009_messages"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove audit logs first (FK to users with no cascade)
    op.execute("DELETE FROM audit_logs")

    # Remove all doctors — cascades to:
    #   doctor_certifications, doctor_languages, doctor_preferences,
    #   doctor_availabilities, doctor_unavailabilities, doctor_reliability_stats,
    #   documents, shift_assignments, shift_offers
    op.execute("DELETE FROM doctors")

    # Remove all institutions — cascades to:
    #   institution_requirements, institution_language_requirements,
    #   institution_sites → shift_templates, shifts →
    #   shift_requirements, shift_language_requirements,
    #   shift_assignments, shift_offers
    op.execute("DELETE FROM institutions")

    # Remove non-admin users — cascades to messages and notifications
    # (doctors already deleted so no FK violation on doctors.user_id)
    op.execute("DELETE FROM users WHERE email != 'datoffaletti@gmail.com'")


def downgrade() -> None:
    # Demo data cannot be restored via downgrade
    pass
