import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import RequireAdmin, get_doctor_service
from app.schemas.common import PaginatedResponse
from app.schemas.doctor import (
    CertificationCreate,
    CertificationRead,
    DoctorBrief,
    DoctorCreate,
    DoctorLanguageCreate,
    DoctorLanguageRead,
    DoctorRead,
    DoctorUpdate,
)
from app.services.doctor import DoctorService

router = APIRouter(prefix="/doctors", tags=["doctors"])

DoctorSvc = Annotated[DoctorService, Depends(get_doctor_service)]


@router.post("/", response_model=DoctorRead, status_code=201)
async def create_doctor(data: DoctorCreate, svc: DoctorSvc, admin: RequireAdmin):
    return await svc.create(data)


@router.get("/", response_model=PaginatedResponse[DoctorBrief])
async def list_doctors(svc: DoctorSvc, admin: RequireAdmin, skip: int = 0, limit: int = 50, search: str | None = None):
    items, total = await svc.get_all(skip=skip, limit=limit, search=search)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{doctor_id}", response_model=DoctorRead)
async def get_doctor(doctor_id: uuid.UUID, svc: DoctorSvc, admin: RequireAdmin):
    doctor = await svc.get(doctor_id)
    if not doctor:
        raise HTTPException(404, "Doctor not found")
    return doctor


@router.patch("/{doctor_id}", response_model=DoctorRead)
async def update_doctor(doctor_id: uuid.UUID, data: DoctorUpdate, svc: DoctorSvc, admin: RequireAdmin):
    doctor = await svc.update(doctor_id, data)
    if not doctor:
        raise HTTPException(404, "Doctor not found")
    return doctor


@router.delete("/{doctor_id}", status_code=204)
async def delete_doctor(doctor_id: uuid.UUID, svc: DoctorSvc, admin: RequireAdmin):
    if not await svc.delete(doctor_id):
        raise HTTPException(404, "Doctor not found")


@router.post("/{doctor_id}/certifications", status_code=201)
async def add_certification(doctor_id: uuid.UUID, data: CertificationCreate, svc: DoctorSvc, admin: RequireAdmin):
    return await svc.add_certification(doctor_id, data)


@router.delete("/{doctor_id}/certifications/{cert_type_id}", status_code=204)
async def remove_certification(doctor_id: uuid.UUID, cert_type_id: int, svc: DoctorSvc, admin: RequireAdmin):
    if not await svc.remove_certification(doctor_id, cert_type_id):
        raise HTTPException(404, "Certification not found")


@router.post("/{doctor_id}/languages", status_code=201)
async def add_language(doctor_id: uuid.UUID, data: DoctorLanguageCreate, svc: DoctorSvc, admin: RequireAdmin):
    return await svc.add_language(doctor_id, data)


@router.delete("/{doctor_id}/languages/{language_id}", status_code=204)
async def remove_language(doctor_id: uuid.UUID, language_id: int, svc: DoctorSvc, admin: RequireAdmin):
    if not await svc.remove_language(doctor_id, language_id):
        raise HTTPException(404, "Language not found")
