import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.requirement import CodeLevel  # noqa: F401 — needed for FK resolution


class Institution(TimestampMixin, Base):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    tax_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    address: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100))
    province: Mapped[str | None] = mapped_column(String(2))
    institution_type: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(default=True)
    cooperative_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cooperatives.id", ondelete="SET NULL"), nullable=True)

    sites: Mapped[list["InstitutionSite"]] = relationship(back_populates="institution", cascade="all, delete-orphan")
    cooperative: Mapped["Cooperative | None"] = relationship(back_populates="institutions")  # noqa: F821


class InstitutionSite(TimestampMixin, Base):
    __tablename__ = "institution_sites"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100))
    province: Mapped[str | None] = mapped_column(String(2))
    lat: Mapped[float | None]
    lon: Mapped[float | None]
    is_active: Mapped[bool] = mapped_column(default=True)

    # Extended fields for Italian medical context
    lodging_available: Mapped[bool] = mapped_column(default=False)
    meal_support: Mapped[bool] = mapped_column(default=False)
    parking_available: Mapped[bool] = mapped_column(default=False)
    min_code_level_id: Mapped[int | None] = mapped_column(ForeignKey("code_levels.id"), default=None)
    requires_independent_work: Mapped[bool] = mapped_column(default=False)
    requires_emergency_vehicle: Mapped[bool] = mapped_column(default=False)
    min_years_experience: Mapped[int] = mapped_column(default=0)

    institution: Mapped["Institution"] = relationship(back_populates="sites")
    min_code_level: Mapped["CodeLevel | None"] = relationship(foreign_keys=[min_code_level_id])
