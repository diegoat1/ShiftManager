import uuid
from datetime import datetime

from sqlalchemy import Enum as SAEnum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.utils.enums import AssignmentStatus

# Assignment source constants
ASSIGNMENT_SOURCE_SELF_APPLIED = "self_applied"
ASSIGNMENT_SOURCE_OFFER_ACCEPTED = "offer_accepted"

_assignment_status_enum = SAEnum(
    AssignmentStatus,
    values_callable=lambda e: [m.value for m in e],
    name="assignmentstatus",
    create_type=False,
)


class ShiftAssignment(TimestampMixin, Base):
    __tablename__ = "shift_assignments"
    __table_args__ = (UniqueConstraint("shift_id", "doctor_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shift_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shifts.id", ondelete="CASCADE"))
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    status: Mapped[AssignmentStatus] = mapped_column(_assignment_status_enum, default=AssignmentStatus.PROPOSED)
    pay_amount: Mapped[float] = mapped_column(default=0.0)
    assigned_at: Mapped[datetime] = mapped_column(server_default=func.now())
    responded_at: Mapped[datetime | None]
    source: Mapped[str | None] = mapped_column(String(20), default=None)

    shift: Mapped["Shift"] = relationship(back_populates="assignments")
    doctor: Mapped["Doctor"] = relationship()
