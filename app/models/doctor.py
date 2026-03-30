import uuid
from datetime import date

from sqlalchemy import Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.requirement import CodeLevel  # noqa: F401 — needed for FK resolution
from app.utils.enums import HomologationStatus

_homologation_enum = SAEnum(
    HomologationStatus,
    values_callable=lambda e: [m.value for m in e],
    name="homologationstatus",
    create_type=False,
)


class Doctor(TimestampMixin, Base):
    __tablename__ = "doctors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), unique=True, default=None)
    fiscal_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(String(255))
    lat: Mapped[float | None]
    lon: Mapped[float | None]
    max_distance_km: Mapped[float] = mapped_column(default=50.0)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Extended fields for Italian medical context
    willing_to_relocate: Mapped[bool] = mapped_column(default=False)
    willing_overnight_stay: Mapped[bool] = mapped_column(default=False)
    max_shifts_per_month: Mapped[int] = mapped_column(default=20)
    max_night_shifts_per_month: Mapped[int | None] = mapped_column(default=None)
    max_code_level_id: Mapped[int | None] = mapped_column(ForeignKey("code_levels.id"), default=None)
    can_work_alone: Mapped[bool] = mapped_column(default=False)
    can_emergency_vehicle: Mapped[bool] = mapped_column(default=False)
    years_experience: Mapped[int] = mapped_column(default=0)

    # Profile fields
    birth_date: Mapped[date | None] = mapped_column(default=None)
    residence_address: Mapped[str | None] = mapped_column(String(500), default=None)
    domicile_city: Mapped[str | None] = mapped_column(String(100), default=None)
    homologation_status: Mapped[HomologationStatus] = mapped_column(_homologation_enum, default=HomologationStatus.PENDING)
    ordine_province: Mapped[str | None] = mapped_column(String(2), default=None)
    ordine_number: Mapped[str | None] = mapped_column(String(20), default=None)
    has_own_vehicle: Mapped[bool] = mapped_column(default=False)
    profile_completion_percent: Mapped[int] = mapped_column(default=0)
    calendar_feed_token: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)

    user: Mapped["User | None"] = relationship(back_populates="doctor", foreign_keys=[user_id])
    certifications: Mapped[list["DoctorCertification"]] = relationship(back_populates="doctor", cascade="all, delete-orphan")
    languages: Mapped[list["DoctorLanguage"]] = relationship(back_populates="doctor", cascade="all, delete-orphan")
    preferences: Mapped["DoctorPreference | None"] = relationship(back_populates="doctor", uselist=False, cascade="all, delete-orphan")
    max_code_level: Mapped["CodeLevel | None"] = relationship(foreign_keys=[max_code_level_id])


class CertificationType(Base):
    __tablename__ = "certification_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    validity_months: Mapped[int | None]


class DoctorCertification(TimestampMixin, Base):
    __tablename__ = "doctor_certifications"
    __table_args__ = (UniqueConstraint("doctor_id", "certification_type_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    certification_type_id: Mapped[int] = mapped_column(ForeignKey("certification_types.id"))
    obtained_date: Mapped[date]
    expiry_date: Mapped[date | None]
    is_active: Mapped[bool] = mapped_column(default=True)

    doctor: Mapped["Doctor"] = relationship(back_populates="certifications")
    certification_type: Mapped["CertificationType"] = relationship()


class Language(Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(5), unique=True)
    name: Mapped[str] = mapped_column(String(50))


class DoctorLanguage(TimestampMixin, Base):
    __tablename__ = "doctor_languages"
    __table_args__ = (UniqueConstraint("doctor_id", "language_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"))
    proficiency_level: Mapped[int] = mapped_column(default=3)

    doctor: Mapped["Doctor"] = relationship(back_populates="languages")
    language: Mapped["Language"] = relationship()


class DoctorPreference(TimestampMixin, Base):
    __tablename__ = "doctor_preferences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), unique=True)
    prefers_day: Mapped[bool] = mapped_column(default=True)
    prefers_night: Mapped[bool] = mapped_column(default=False)
    prefers_weekends: Mapped[bool] = mapped_column(default=False)
    avoids_weekends: Mapped[bool] = mapped_column(default=False)
    preferred_institution_types: Mapped[str | None] = mapped_column(String(500))
    preferred_code_levels: Mapped[str | None] = mapped_column(String(200))
    min_pay_per_shift: Mapped[float | None] = mapped_column(default=None)
    max_preferred_distance_km: Mapped[float | None] = mapped_column(default=None)

    doctor: Mapped["Doctor"] = relationship(back_populates="preferences")
