import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.utils.enums import VerificationStatus


class DocumentType(Base):
    __tablename__ = "document_types"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500), default=None)
    validity_months: Mapped[int | None] = mapped_column(default=None)
    is_mandatory: Mapped[bool] = mapped_column(default=False)


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    doctor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("doctors.id", ondelete="CASCADE"))
    document_type_id: Mapped[int] = mapped_column(ForeignKey("document_types.id"))
    file_path: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(255))
    file_size_bytes: Mapped[int] = mapped_column(default=0)
    mime_type: Mapped[str] = mapped_column(String(100))
    uploaded_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    issued_at: Mapped[date | None] = mapped_column(default=None)
    expires_at: Mapped[date | None] = mapped_column(default=None)
    verification_status: Mapped[VerificationStatus] = mapped_column(default=VerificationStatus.PENDING)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    verified_at: Mapped[datetime | None] = mapped_column(default=None)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), default=None)

    doctor: Mapped["Doctor"] = relationship()
    document_type: Mapped["DocumentType"] = relationship()
    verifier: Mapped["User | None"] = relationship(foreign_keys=[verified_by])


from app.models.doctor import Doctor  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
