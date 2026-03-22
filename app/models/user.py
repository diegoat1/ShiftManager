import uuid
from datetime import datetime

from sqlalchemy import Enum as SAEnum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.utils.enums import UserRole

_userrole_enum = SAEnum(
    UserRole,
    values_callable=lambda e: [m.value for m in e],
    name="userrole",
    create_type=False,
)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(_userrole_enum, default=UserRole.MEDICO)
    is_active: Mapped[bool] = mapped_column(default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(default=None)

    doctor: Mapped["Doctor | None"] = relationship(back_populates="user", uselist=False)


# Avoid circular import — resolved via string reference in relationship
from app.models.doctor import Doctor  # noqa: E402, F401
