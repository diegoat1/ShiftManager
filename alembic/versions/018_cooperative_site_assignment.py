"""Move cooperative relationship from Institution to Site-level temporal assignments.

Creates cooperative_site_assignments table, migrates existing institution-cooperative
relationships to site-level assignments, and drops institutions.cooperative_id.

Downgrade is lossy by design: per-site temporal assignments compress to a single
institution-level FK. Institutions with cooperative_id but no sites lose the
relationship entirely (the new model only tracks site-level contracts).

Revision ID: 018_cooperative_site_assignment
Revises: 017_move_site_type
Create Date: 2026-04-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018_cooperative_site_assignment"
down_revision: str = "017_move_site_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create cooperative_site_assignments table
    op.create_table(
        "cooperative_site_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cooperative_id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["cooperative_id"], ["cooperatives.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["site_id"], ["institution_sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_coop_site_dates", "cooperative_site_assignments",
        ["site_id", "start_date", "end_date"],
    )

    # 2. Data migration: institution.cooperative_id → site-level assignments
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("""
            SELECT s.id AS site_id, i.cooperative_id, CAST(s.created_at AS DATE) AS start_date
            FROM institution_sites s
            JOIN institutions i ON s.institution_id = i.id
            WHERE i.cooperative_id IS NOT NULL
        """)
    ).fetchall()
    if rows:
        conn.execute(
            sa.text("""
                INSERT INTO cooperative_site_assignments (id, cooperative_id, site_id, start_date, notes, created_at, updated_at)
                VALUES (gen_random_uuid(), :coop_id, :site_id, :start_date,
                        'Migrated from institutions.cooperative_id', NOW(), NOW())
            """),
            [{"coop_id": r.cooperative_id, "site_id": r.site_id, "start_date": r.start_date} for r in rows],
        )

    # 3. Drop old FK column
    op.drop_column("institutions", "cooperative_id")


def downgrade() -> None:
    # 1. Re-add cooperative_id column
    op.add_column(
        "institutions",
        sa.Column("cooperative_id", sa.Uuid(),
                  sa.ForeignKey("cooperatives.id", ondelete="SET NULL"),
                  nullable=True),
    )

    # 2. Lossy data migration: pick first active assignment per institution
    conn = op.get_bind()
    conn.execute(
        sa.text("""
            UPDATE institutions i
            SET cooperative_id = sub.cooperative_id
            FROM (
                SELECT DISTINCT ON (s.institution_id)
                    s.institution_id, csa.cooperative_id
                FROM cooperative_site_assignments csa
                JOIN institution_sites s ON csa.site_id = s.id
                WHERE csa.end_date IS NULL
                ORDER BY s.institution_id, csa.start_date DESC
            ) sub
            WHERE i.id = sub.institution_id
        """)
    )

    # 3. Drop new table
    op.drop_index("ix_coop_site_dates", table_name="cooperative_site_assignments")
    op.drop_table("cooperative_site_assignments")
