"""initial_schema

Revision ID: 001_initial
Revises:
Create Date: 2026-03-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Reference tables (no FKs) ---
    op.create_table(
        "code_levels",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("description", sa.String(200), nullable=True),
        sa.Column("severity_order", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "certification_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("validity_months", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "languages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(5), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    # --- Core entity tables ---
    op.create_table(
        "doctors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fiscal_code", sa.String(16), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("max_distance_km", sa.Float(), server_default="50.0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("willing_to_relocate", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("willing_overnight_stay", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("max_shifts_per_month", sa.Integer(), server_default="20", nullable=False),
        sa.Column("max_night_shifts_per_month", sa.Integer(), nullable=True),
        sa.Column("max_code_level_id", sa.Integer(), nullable=True),
        sa.Column("can_work_alone", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("can_emergency_vehicle", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("years_experience", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["max_code_level_id"], ["code_levels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_doctors_fiscal_code", "doctors", ["fiscal_code"], unique=True)
    op.create_index("ix_doctors_email", "doctors", ["email"], unique=True)

    op.create_table(
        "institutions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("tax_code", sa.String(16), nullable=False),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("province", sa.String(2), nullable=True),
        sa.Column("institution_type", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_institutions_tax_code", "institutions", ["tax_code"], unique=True)

    # --- Tables with FK to core entities ---
    op.create_table(
        "institution_sites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("province", sa.String(2), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("lodging_available", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("meal_support", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("parking_available", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("min_code_level_id", sa.Integer(), nullable=True),
        sa.Column("requires_independent_work", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("requires_emergency_vehicle", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("min_years_experience", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["min_code_level_id"], ["code_levels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "doctor_certifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doctor_id", sa.Uuid(), nullable=False),
        sa.Column("certification_type_id", sa.Integer(), nullable=False),
        sa.Column("obtained_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["certification_type_id"], ["certification_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id", "certification_type_id"),
    )

    op.create_table(
        "doctor_languages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doctor_id", sa.Uuid(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.Column("proficiency_level", sa.Integer(), server_default="3", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_id"], ["languages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id", "language_id"),
    )

    op.create_table(
        "doctor_preferences",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doctor_id", sa.Uuid(), nullable=False),
        sa.Column("prefers_day", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("prefers_night", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("prefers_weekends", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("avoids_weekends", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("preferred_institution_types", sa.String(500), nullable=True),
        sa.Column("preferred_code_levels", sa.String(200), nullable=True),
        sa.Column("min_pay_per_shift", sa.Float(), nullable=True),
        sa.Column("max_preferred_distance_km", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id"),
    )

    op.create_table(
        "doctor_availabilities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doctor_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("availability_type", sa.String(50), server_default="available", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("doctor_id", "date", "start_time", "end_time"),
    )

    op.create_table(
        "doctor_unavailabilities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doctor_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(50), server_default="other", nullable=False),
        sa.Column("is_approved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "institution_requirements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("certification_type_id", sa.Integer(), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["certification_type_id"], ["certification_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "certification_type_id"),
    )

    op.create_table(
        "institution_language_requirements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("institution_id", sa.Uuid(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.Column("min_proficiency", sa.Integer(), server_default="3", nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_id"], ["languages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("institution_id", "language_id"),
    )

    # --- Shift tables ---
    op.create_table(
        "shift_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("required_doctors", sa.Integer(), server_default="1", nullable=False),
        sa.Column("base_pay", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("is_night", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["institution_sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "shifts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("start_datetime", sa.DateTime(), nullable=False),
        sa.Column("end_datetime", sa.DateTime(), nullable=False),
        sa.Column("required_doctors", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(50), server_default="draft", nullable=False),
        sa.Column("base_pay", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("urgent_multiplier", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("is_night", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("shift_type", sa.String(20), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="3", nullable=False),
        sa.Column("min_code_level_id", sa.Integer(), nullable=True),
        sa.Column("requires_independent_work", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("requires_emergency_vehicle", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("min_years_experience", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["shift_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["site_id"], ["institution_sites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["min_code_level_id"], ["code_levels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "shift_requirements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("certification_type_id", sa.Integer(), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["certification_type_id"], ["certification_types.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shift_id", "certification_type_id"),
    )

    op.create_table(
        "shift_language_requirements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("language_id", sa.Integer(), nullable=False),
        sa.Column("min_proficiency", sa.Integer(), server_default="3", nullable=False),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["language_id"], ["languages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shift_id", "language_id"),
    )

    op.create_table(
        "shift_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("shift_id", sa.Uuid(), nullable=False),
        sa.Column("doctor_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(50), server_default="proposed", nullable=False),
        sa.Column("pay_amount", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("assigned_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["shift_id"], ["shifts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shift_id", "doctor_id"),
    )


def downgrade() -> None:
    op.drop_table("shift_assignments")
    op.drop_table("shift_language_requirements")
    op.drop_table("shift_requirements")
    op.drop_table("shifts")
    op.drop_table("shift_templates")
    op.drop_table("institution_language_requirements")
    op.drop_table("institution_requirements")
    op.drop_table("doctor_unavailabilities")
    op.drop_table("doctor_availabilities")
    op.drop_table("doctor_preferences")
    op.drop_table("doctor_languages")
    op.drop_table("doctor_certifications")
    op.drop_table("institution_sites")
    op.drop_index("ix_institutions_tax_code", table_name="institutions")
    op.drop_table("institutions")
    op.drop_index("ix_doctors_email", table_name="doctors")
    op.drop_index("ix_doctors_fiscal_code", table_name="doctors")
    op.drop_table("doctors")
    op.drop_table("languages")
    op.drop_table("certification_types")
    op.drop_table("code_levels")
