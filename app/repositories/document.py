import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentType
from app.repositories.base import BaseRepository
from app.utils.enums import VerificationStatus


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    async def get_by_doctor(self, doctor_id: uuid.UUID) -> list[Document]:
        stmt = (
            select(Document)
            .options(selectinload(Document.document_type))
            .where(Document.doctor_id == doctor_id)
            .order_by(Document.uploaded_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_status(self, status: VerificationStatus, skip: int = 0, limit: int = 50) -> list[Document]:
        stmt = (
            select(Document)
            .options(selectinload(Document.document_type), selectinload(Document.doctor))
            .where(Document.verification_status == status)
            .order_by(Document.uploaded_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_documents(self, skip: int = 0, limit: int = 50, status: str | None = None) -> list[Document]:
        stmt = (
            select(Document)
            .options(selectinload(Document.document_type), selectinload(Document.doctor))
            .order_by(Document.uploaded_at.desc())
        )
        if status:
            stmt = stmt.where(Document.verification_status == VerificationStatus(status))
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_relations(self, doc_id: uuid.UUID) -> Document | None:
        stmt = (
            select(Document)
            .options(selectinload(Document.document_type), selectinload(Document.doctor))
            .where(Document.id == doc_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_approved_by_doctor(self, doctor_id: uuid.UUID) -> list[Document]:
        stmt = (
            select(Document)
            .options(selectinload(Document.document_type))
            .where(
                Document.doctor_id == doctor_id,
                Document.verification_status == VerificationStatus.APPROVED,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class DocumentTypeRepository(BaseRepository[DocumentType]):
    def __init__(self, session: AsyncSession):
        super().__init__(DocumentType, session)

    async def get_by_code(self, code: str) -> DocumentType | None:
        result = await self.session.execute(select(DocumentType).where(DocumentType.code == code))
        return result.scalar_one_or_none()

    async def get_mandatory(self) -> list[DocumentType]:
        result = await self.session.execute(
            select(DocumentType).where(DocumentType.is_mandatory == True)
        )
        return list(result.scalars().all())
