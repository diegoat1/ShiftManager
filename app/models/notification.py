import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str | None] = mapped_column(String(1000), default=None)
    channel: Mapped[str] = mapped_column(String(20), default="in_app")
    status: Mapped[str] = mapped_column(String(20), default="unread")
    sent_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    read_at: Mapped[datetime | None] = mapped_column(default=None)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), default=None)
    related_entity_id: Mapped[str | None] = mapped_column(String(50), default=None)

    user: Mapped["User"] = relationship()


from app.models.user import User  # noqa: E402, F401
