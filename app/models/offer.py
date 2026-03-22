import uuid
from datetime import datetime

from sqlalchemy import Enum as SAEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.utils.enums import OfferStatus

_offer_enum = SAEnum(
    OfferStatus,
    values_callable=lambda e: [m.value for m in e],
    name="offerstatus",
    create_type=False,
)


class ShiftOffer(TimestampMixin, Base):
    __tablename__ = "shift_offers"
    __table_args__ = (UniqueConstraint("shift_id", "doctor_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shift_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shifts.id", ondelete="CASCADE"))
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    status: Mapped[OfferStatus] = mapped_column(_offer_enum, default=OfferStatus.PROPOSED)
    offered_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(default=None)
    responded_at: Mapped[datetime | None] = mapped_column(default=None)
    response_note: Mapped[str | None] = mapped_column(String(500), default=None)
    rank_snapshot: Mapped[int | None] = mapped_column(default=None)
    score_snapshot: Mapped[int | None] = mapped_column(default=None)
    proposed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)

    shift: Mapped["Shift"] = relationship(back_populates="offers")
    doctor: Mapped["Doctor"] = relationship()
    proposer: Mapped["User | None"] = relationship(foreign_keys=[proposed_by])


from app.models.doctor import Doctor  # noqa: E402, F401
from app.models.shift import Shift  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
