from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentDoctor, get_doctor_service
from app.schemas.doctor import (
    CertificationCreate,
    CertificationRead,
    DoctorLanguageCreate,
    DoctorLanguageRead,
)
from app.services.doctor import DoctorService

router = APIRouter(prefix="/me", tags=["me-certifications"])

DoctorSvc = Annotated[DoctorService, Depends(get_doctor_service)]


@router.get("/certifications", response_model=list[CertificationRead])
async def get_my_certifications(doctor: CurrentDoctor, svc: DoctorSvc):
    return await svc.get_certifications(doctor.id)


@router.post("/certifications", response_model=CertificationRead, status_code=201)
async def add_my_certification(data: CertificationCreate, doctor: CurrentDoctor, svc: DoctorSvc):
    try:
        return await svc.add_certification(doctor.id, data)
    except IntegrityError:
        raise HTTPException(409, "Certification already exists for this doctor")


@router.delete("/certifications/{cert_type_id}", status_code=204)
async def remove_my_certification(cert_type_id: int, doctor: CurrentDoctor, svc: DoctorSvc):
    if not await svc.remove_certification(doctor.id, cert_type_id):
        raise HTTPException(404, "Certification not found")


@router.get("/languages", response_model=list[DoctorLanguageRead])
async def get_my_languages(doctor: CurrentDoctor, svc: DoctorSvc):
    return await svc.get_languages(doctor.id)


@router.post("/languages", response_model=DoctorLanguageRead, status_code=201)
async def add_my_language(data: DoctorLanguageCreate, doctor: CurrentDoctor, svc: DoctorSvc):
    try:
        return await svc.add_language(doctor.id, data)
    except IntegrityError:
        raise HTTPException(409, "Language already exists for this doctor")


@router.delete("/languages/{language_id}", status_code=204)
async def remove_my_language(language_id: int, doctor: CurrentDoctor, svc: DoctorSvc):
    if not await svc.remove_language(doctor.id, language_id):
        raise HTTPException(404, "Language not found")
