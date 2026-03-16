import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CodeLevel(Base):
    __tablename__ = "code_levels"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    description: Mapped[str | None] = mapped_column(String(200))
    severity_order: Mapped[int] = mapped_column(default=0)


class InstitutionRequirement(Base):
    __tablename__ = "institution_requirements"
    __table_args__ = (UniqueConstraint("institution_id", "certification_type_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"))
    certification_type_id: Mapped[int] = mapped_column(ForeignKey("certification_types.id"))
    is_mandatory: Mapped[bool] = mapped_column(default=True)

    certification_type: Mapped["CertificationType"] = relationship()


class InstitutionLanguageRequirement(Base):
    __tablename__ = "institution_language_requirements"
    __table_args__ = (UniqueConstraint("institution_id", "language_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id", ondelete="CASCADE"))
    language_id: Mapped[int] = mapped_column(ForeignKey("languages.id"))
    min_proficiency: Mapped[int] = mapped_column(default=3)

    language: Mapped["Language"] = relationship()
