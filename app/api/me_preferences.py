from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentDoctor, get_doctor_service
from app.schemas.doctor import DoctorPreferenceCreate, DoctorPreferenceRead
from app.services.doctor import DoctorService

router = APIRouter(prefix="/me", tags=["me-preferences"])

DoctorSvc = Annotated[DoctorService, Depends(get_doctor_service)]


@router.get("/preferences", response_model=DoctorPreferenceRead | None)
async def get_my_preferences(doctor: CurrentDoctor, svc: DoctorSvc):
    return await svc.get_preferences(doctor.id)


@router.put("/preferences", response_model=DoctorPreferenceRead)
async def update_my_preferences(data: DoctorPreferenceCreate, doctor: CurrentDoctor, svc: DoctorSvc):
    return await svc.upsert_preferences(doctor.id, data)
