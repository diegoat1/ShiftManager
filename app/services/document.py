import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.document import DocumentRepository, DocumentTypeRepository
from app.utils.enums import VerificationStatus


class DocumentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DocumentRepository(session)
        self.type_repo = DocumentTypeRepository(session)

    async def get_doctor_documents(self, doctor_id: uuid.UUID) -> list[Document]:
        return await self.repo.get_by_doctor(doctor_id)

    async def upload(
        self,
        doctor_id: uuid.UUID,
        document_type_id: int,
        file_path: str,
        original_filename: str,
        file_size_bytes: int,
        mime_type: str,
        issued_at=None,
        expires_at=None,
    ) -> Document:
        doc = await self.repo.create(
            doctor_id=doctor_id,
            document_type_id=document_type_id,
            file_path=file_path,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            mime_type=mime_type,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        await self.session.commit()
        return doc

    async def delete_document(self, doc_id: uuid.UUID, doctor_id: uuid.UUID) -> bool:
        doc = await self.repo.get_by_id(doc_id)
        if not doc or doc.doctor_id != doctor_id:
            return False
        if doc.verification_status != VerificationStatus.PENDING:
            return False
        await self.repo.delete(doc)
        await self.session.commit()
        return True

    async def get_all_documents(self, skip: int = 0, limit: int = 50, status: str | None = None):
        return await self.repo.get_all_documents(skip=skip, limit=limit, status=status)

    async def get_doctor_documents_admin(self, doctor_id: uuid.UUID):
        return await self.repo.get_by_doctor(doctor_id)

    async def approve(self, doc_id: uuid.UUID, verified_by: uuid.UUID) -> Document | None:
        doc = await self.repo.get_with_relations(doc_id)
        if not doc:
            return None
        doc.verification_status = VerificationStatus.APPROVED
        doc.verified_by = verified_by
        doc.verified_at = datetime.utcnow()
        doc.rejection_reason = None
        await self.session.flush()
        await self.session.commit()
        return doc

    async def reject(self, doc_id: uuid.UUID, verified_by: uuid.UUID, reason: str) -> Document | None:
        doc = await self.repo.get_with_relations(doc_id)
        if not doc:
            return None
        doc.verification_status = VerificationStatus.REJECTED
        doc.verified_by = verified_by
        doc.verified_at = datetime.utcnow()
        doc.rejection_reason = reason
        await self.session.flush()
        await self.session.commit()
        return doc

    async def get_document_types(self):
        return await self.type_repo.get_all(limit=100)

    async def get_approved_by_doctor(self, doctor_id: uuid.UUID):
        return await self.repo.get_approved_by_doctor(doctor_id)
