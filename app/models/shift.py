import uuid
from datetime import date, datetime, time

from sqlalchemy import Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.requirement import CodeLevel  # noqa: F401 — needed for FK resolution
from app.utils.enums import ShiftStatus

_shift_status_enum = SAEnum(
    ShiftStatus,
    values_callable=lambda e: [m.value for m in e],
    name="shiftstatus",
    create_type=False,
)


class ShiftTemplate(TimestampMixin, Base):
    __tablename__ = "shift_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution_sites.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    start_time: Mapped[time]
    end_time: Mapped[time]
    required_doctors: Mapped[int] = mapped_column(default=1)
    base_pay: Mapped[float] = mapped_column(default=0.0)
    is_night: Mapped[bool] = mapped_column(default=False)
    min_code_level_id: Mapped[int | None] = mapped_column(ForeignKey("code_levels.id"), default=None)
    requires_emergency_vehicle: Mapped[bool] = mapped_column(default=False)

    site: Mapped["InstitutionSite"] = relationship()
    min_code_level: Mapped["CodeLevel | None"] = relationship(foreign_keys=[min_code_level_id])


class Shift(TimestampMixin, Base):
    __tablename__ = "shifts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shift_templates.id", ondelete="SET NULL"))
    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institution_sites.id", ondelete="CASCADE"))
    date: Mapped[date]
    start_datetime: Mapped[datetime]
    end_datetime: Mapped[datetime]
    required_doctors: Mapped[int] = mapped_column(default=1)
    status: Mapped[ShiftStatus] = mapped_column(_shift_status_enum, default=ShiftStatus.DRAFT)
    base_pay: Mapped[float] = mapped_column(default=0.0)
    urgent_multiplier: Mapped[float] = mapped_column(default=1.0)
    is_night: Mapped[bool] = mapped_column(default=False)

    # Extended fields for Italian medical context
    shift_type: Mapped[str | None] = mapped_column(String(20), default=None)
    priority: Mapped[int] = mapped_column(default=3)
    min_code_level_id: Mapped[int | None] = mapped_column(ForeignKey("code_levels.id"), default=None)
    requires_independent_work: Mapped[bool] = mapped_column(default=False)
    requires_emergency_vehicle: Mapped[bool] = mapped_column(default=False)
    min_years_experience: Mapped[int] = mapped_column(default=0)

    site: Mapped["InstitutionSite"] = relationship()
    requirements: Mapped[list["ShiftRequirement"]] = relationship(back_populates="shift", cascade="all, delete-orphan")
    language_requirements: Mapped[list["ShiftLanguageRequirement"]] = relationship(back_populates="shift", cascade="all, delete-orphan")
    assignments: Mapped[list["ShiftAssignment"]] = relationship(back_populates="shift")
    offers: Mapped[list["ShiftOffer"]] = relationship(back_populates="shift")
    min_code_level: Mapped["CodeLevel | None"] = relationship(foreign_keys=[min_code_level_id])


class ShiftRequirement(Base):
    __tablename__ = "shift_requirements"
    __table_args__ = (UniqueConstraint("shift_id", "certification_type_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shift_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shifts.id", ondelete="CASCADE"))
    certification_type_id: Mapped[int] = mapped_column(ForeignKey("certification_types.id"))
    is_mandatory: Mapped[bool] = mapped_column(default=True)

    shift: Mapped["Shift"] = relationship(back_populates="requirements")
    certification_type: Mapped["CertificationType"] = relationship()


class ShiftLanguageRequirement(Base):
    __tablename__ = "shift_language_requirements"
    __table_args__ = (UniqueConstraint("shift_id", "language_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    shift_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shifts.id", ondelete="CASCADE"))
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"))
    min_proficiency: Mapped[int] = mapped_column(default=3)

    shift: Mapped["Shift"] = relationship(back_populates="language_requirements")
    language: Mapped["Language"] = relationship()
