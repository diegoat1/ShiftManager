import uuid
from datetime import date

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class Cooperative(TimestampMixin, Base):
    __tablename__ = "cooperatives"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    partita_iva: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    address: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100))
    province: Mapped[str | None] = mapped_column(String(2))
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(default=True)

    site_assignments: Mapped[list["CooperativeSiteAssignment"]] = relationship(
        back_populates="cooperative"
    )


class CooperativeSiteAssignment(TimestampMixin, Base):
    """Temporal link between a cooperative and a site.

    Active assignment: end_date IS NULL (ongoing).
    Historical: end_date IS NOT NULL.
    One active assignment per site at a time — enforced by service layer.
    """

    __tablename__ = "cooperative_site_assignments"
    __table_args__ = (
        Index("ix_coop_site_dates", "site_id", "start_date", "end_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cooperative_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cooperatives.id", ondelete="CASCADE")
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("institution_sites.id", ondelete="CASCADE")
    )
    start_date: Mapped[date]
    end_date: Mapped[date | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    cooperative: Mapped["Cooperative"] = relationship(back_populates="site_assignments")
    site: Mapped["InstitutionSite"] = relationship(back_populates="cooperative_assignments")  # noqa: F821
