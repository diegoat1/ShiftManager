from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentDoctor, get_doctor_service
from app.schemas.doctor import DoctorProfileUpdate, DoctorRead
from app.services.doctor import DoctorService

router = APIRouter(prefix="/me", tags=["me"])

DoctorSvc = Annotated[DoctorService, Depends(get_doctor_service)]


@router.get("/profile", response_model=DoctorRead)
async def get_profile(doctor: CurrentDoctor):
    return doctor


@router.patch("/profile", response_model=DoctorRead)
async def update_profile(data: DoctorProfileUpdate, doctor: CurrentDoctor, svc: DoctorSvc):
    updated = await svc.update_profile(doctor.id, data)
    if not updated:
        raise HTTPException(500, "Failed to update profile")
    return updated
