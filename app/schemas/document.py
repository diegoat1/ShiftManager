import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.utils.enums import VerificationStatus


class DocumentTypeRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None = None
    validity_months: int | None = None
    is_mandatory: bool


class DocumentRead(BaseModel):
    id: uuid.UUID
    doctor_id: uuid.UUID
    document_type_id: int
    document_type: DocumentTypeRead | None = None
    original_filename: str
    file_size_bytes: int
    mime_type: str
    uploaded_at: datetime
    issued_at: date | None = None
    expires_at: date | None = None
    verification_status: VerificationStatus
    verified_at: datetime | None = None
    rejection_reason: str | None = None
    created_at: datetime


class DocumentUpload(BaseModel):
    document_type_id: int
    issued_at: date | None = None
    expires_at: date | None = None


class DocumentVerify(BaseModel):
    status: VerificationStatus
    rejection_reason: str | None = None
