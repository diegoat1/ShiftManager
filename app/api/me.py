from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, get_doctor_service
from app.schemas.doctor import DoctorProfileUpdate, DoctorRead
from app.services.doctor import DoctorService
from app.utils.enums import UserRole

router = APIRouter(prefix="/me", tags=["me"])

DoctorSvc = Annotated[DoctorService, Depends(get_doctor_service)]


@router.get("/profile", response_model=DoctorRead)
async def get_profile(user: CurrentUser, svc: DoctorSvc):
    if user.role != UserRole.MEDICO:
        raise HTTPException(403, "Only doctors can access their profile")
    doctor = await svc.get_by_user_id(user.id)
    if not doctor:
        raise HTTPException(404, "Doctor profile not found")
    return doctor


@router.patch("/profile", response_model=DoctorRead)
async def update_profile(data: DoctorProfileUpdate, user: CurrentUser, svc: DoctorSvc):
    if user.role != UserRole.MEDICO:
        raise HTTPException(403, "Only doctors can update their profile")
    doctor = await svc.get_by_user_id(user.id)
    if not doctor:
        raise HTTPException(404, "Doctor profile not found")
    updated = await svc.update_profile(doctor.id, data)
    if not updated:
        raise HTTPException(500, "Failed to update profile")
    return updated
