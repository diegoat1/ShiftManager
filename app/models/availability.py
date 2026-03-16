import uuid
from datetime import date, time

from sqlalchemy import Enum as SAEnum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.utils.enums import AvailabilityType, UnavailabilityReason

_availability_type_enum = SAEnum(
    AvailabilityType,
    values_callable=lambda e: [m.value for m in e],
    name="availabilitytype",
    create_type=False,
)
_unavailability_reason_enum = SAEnum(
    UnavailabilityReason,
    values_callable=lambda e: [m.value for m in e],
    name="unavailabilityreason",
    create_type=False,
)


class DoctorAvailability(TimestampMixin, Base):
    __tablename__ = "doctor_availabilities"
    __table_args__ = (UniqueConstraint("doctor_id", "date", "start_time", "end_time"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    date: Mapped[date]
    start_time: Mapped[time]
    end_time: Mapped[time]
    availability_type: Mapped[AvailabilityType] = mapped_column(_availability_type_enum, default=AvailabilityType.AVAILABLE)

    doctor: Mapped["Doctor"] = relationship()


class DoctorUnavailability(TimestampMixin, Base):
    __tablename__ = "doctor_unavailabilities"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    start_date: Mapped[date]
    end_date: Mapped[date]
    reason: Mapped[UnavailabilityReason] = mapped_column(_unavailability_reason_enum, default=UnavailabilityReason.OTHER)
    is_approved: Mapped[bool] = mapped_column(default=False)

    doctor: Mapped["Doctor"] = relationship()
