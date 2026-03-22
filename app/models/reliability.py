import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DoctorReliabilityStats(Base):
    __tablename__ = "doctor_reliability_stats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"), unique=True)
    total_offers_received: Mapped[int] = mapped_column(default=0)
    total_offers_accepted: Mapped[int] = mapped_column(default=0)
    total_offers_rejected: Mapped[int] = mapped_column(default=0)
    total_offers_expired: Mapped[int] = mapped_column(default=0)
    total_cancellations: Mapped[int] = mapped_column(default=0)
    avg_response_time_minutes: Mapped[float] = mapped_column(default=0.0)
    acceptance_rate: Mapped[float] = mapped_column(default=0.0)
    reliability_score: Mapped[float] = mapped_column(default=0.0)
    last_calculated_at: Mapped[datetime | None] = mapped_column(default=None)
