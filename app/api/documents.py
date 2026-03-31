import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import CurrentUser, get_document_service, get_doctor_service
from app.core.config import settings
from app.schemas.document import DocumentRead
from app.services.doctor import DoctorService
from app.services.document import DocumentService
from app.utils.enums import UserRole

router = APIRouter(prefix="/me/documents", tags=["documents"])

DocSvc = Annotated[DocumentService, Depends(get_document_service)]
DoctorSvc = Annotated[DoctorService, Depends(get_doctor_service)]

ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}


@router.get("/", response_model=list[DocumentRead])
async def list_my_documents(user: CurrentUser, svc: DocSvc, doctor_svc: DoctorSvc):
    if user.role != UserRole.MEDICO:
        raise HTTPException(403, "Only doctors can access documents")
    doctor = await doctor_svc.get_by_user_id(user.id)
    if not doctor:
        raise HTTPException(404, "Doctor profile not found")
    return await svc.get_doctor_documents(doctor.id)


@router.post("/", response_model=DocumentRead, status_code=201)
async def upload_document(
    user: CurrentUser,
    svc: DocSvc,
    doctor_svc: DoctorSvc,
    file: UploadFile = File(...),
    document_type_id: int = Form(...),
    issued_at: str | None = Form(None),
    expires_at: str | None = Form(None),
):
    if user.role != UserRole.MEDICO:
        raise HTTPException(403, "Only doctors can upload documents")
    doctor = await doctor_svc.get_by_user_id(user.id)
    if not doctor:
        raise HTTPException(404, "Doctor profile not found")

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(400, f"File type {file.content_type} not allowed")

    content = await file.read()
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(400, f"File exceeds {settings.MAX_FILE_SIZE_MB}MB limit")

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR) / str(doctor.id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4()
    ext = Path(file.filename or "file").suffix
    file_path = upload_dir / f"{file_id}{ext}"
    file_path.write_bytes(content)

    from datetime import date as date_type
    issued = date_type.fromisoformat(issued_at) if issued_at else None
    expires = date_type.fromisoformat(expires_at) if expires_at else None

    return await svc.upload(
        doctor_id=doctor.id,
        document_type_id=document_type_id,
        file_path=str(file_path),
        original_filename=file.filename or "unknown",
        file_size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream",
        issued_at=issued,
        expires_at=expires,
    )


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: uuid.UUID, user: CurrentUser, svc: DocSvc, doctor_svc: DoctorSvc):
    if user.role != UserRole.MEDICO:
        raise HTTPException(403, "Only doctors can delete documents")
    doctor = await doctor_svc.get_by_user_id(user.id)
    if not doctor:
        raise HTTPException(404, "Doctor profile not found")
    if not await svc.delete_document(doc_id, doctor.id):
        raise HTTPException(404, "Document not found or not deletable")


@router.get("/{doc_id}/download")
async def download_document(doc_id: uuid.UUID, user: CurrentUser, svc: DocSvc, doctor_svc: DoctorSvc):
    if user.role != UserRole.MEDICO:
        raise HTTPException(403, "Only doctors can access documents")
    doctor = await doctor_svc.get_by_user_id(user.id)
    if not doctor:
        raise HTTPException(404, "Doctor profile not found")
    doc = await svc.repo.get_by_id(doc_id)
    if not doc or doc.doctor_id != doctor.id:
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
