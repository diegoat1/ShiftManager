import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from app.api.deps import RequireAdmin, get_document_service
from app.core.config import settings
from app.schemas.document import DocumentRead, DocumentTypeRead, DocumentVerify
from app.services.document import DocumentService
from app.utils.enums import VerificationStatus

router = APIRouter(prefix="/admin/documents", tags=["admin-documents"])

DocSvc = Annotated[DocumentService, Depends(get_document_service)]


@router.get("/", response_model=list[DocumentRead])
async def list_all_documents(
    admin: RequireAdmin,
    svc: DocSvc,
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
):
    return await svc.get_all_documents(skip=skip, limit=limit, status=status)


@router.get("/doctors/{doctor_id}", response_model=list[DocumentRead])
async def list_doctor_documents(doctor_id: uuid.UUID, admin: RequireAdmin, svc: DocSvc):
    return await svc.get_doctor_documents_admin(doctor_id)


@router.post("/{doc_id}/approve", response_model=DocumentRead)
async def approve_document(doc_id: uuid.UUID, admin: RequireAdmin, svc: DocSvc):
    doc = await svc.approve(doc_id, admin.id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.post("/{doc_id}/reject", response_model=DocumentRead)
async def reject_document(doc_id: uuid.UUID, data: DocumentVerify, admin: RequireAdmin, svc: DocSvc):
    if not data.rejection_reason:
        raise HTTPException(400, "Rejection reason is required")
    doc = await svc.reject(doc_id, admin.id, data.rejection_reason)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.get("/{doc_id}/download")
async def admin_download_document(doc_id: uuid.UUID, admin: RequireAdmin, svc: DocSvc):
    doc = await svc.repo.get_by_id(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    file_path = Path(doc.file_path)
    if not file_path.is_absolute():
        file_path = Path(settings.UPLOAD_DIR).parent / doc.file_path
    if not file_path.exists():
        raise HTTPException(404, "File not found on server")
    return FileResponse(
        path=str(file_path),
        filename=doc.original_filename,
        media_type=doc.mime_type,
    )


# Document types endpoint (accessible by any authenticated user)
types_router = APIRouter(tags=["document-types"])


@types_router.get("/api/v1/document-types/", response_model=list[DocumentTypeRead])
async def list_document_types(svc: DocSvc):
    return await svc.get_document_types()
