import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import RequireAdmin, get_availability_service
from app.schemas.availability import (
    AvailabilityCreate,
    AvailabilityRead,
    BulkAvailabilityCreate,
    UnavailabilityCreate,
    UnavailabilityRead,
)
from app.services.availability import AvailabilityService

router = APIRouter(prefix="/doctors/{doctor_id}", tags=["availability"])

AvailSvc = Annotated[AvailabilityService, Depends(get_availability_service)]


@router.post("/availability", response_model=AvailabilityRead, status_code=201)
async def set_availability(doctor_id: uuid.UUID, data: AvailabilityCreate, svc: AvailSvc, admin: RequireAdmin):
    return await svc.set_availability(doctor_id, data)


@router.post("/availability/bulk", status_code=201)
async def bulk_set_availability(doctor_id: uuid.UUID, data: BulkAvailabilityCreate, svc: AvailSvc, admin: RequireAdmin):
    return await svc.bulk_set_availability(doctor_id, data)


@router.get("/availability", response_model=list[AvailabilityRead])
async def get_availability(
    doctor_id: uuid.UUID,
    svc: AvailSvc,
    admin: RequireAdmin,
    start: date = Query(...),
    end: date = Query(...),
):
    return await svc.get_availability(doctor_id, start, end)


@router.post("/unavailability", response_model=UnavailabilityRead, status_code=201)
async def create_unavailability(doctor_id: uuid.UUID, data: UnavailabilityCreate, svc: AvailSvc, admin: RequireAdmin):
    return await svc.create_unavailability(doctor_id, data)


@router.get("/unavailability", response_model=list[UnavailabilityRead])
async def get_unavailabilities(
    doctor_id: uuid.UUID,
    svc: AvailSvc,
    admin: RequireAdmin,
    start: date | None = None,
    end: date | None = None,
):
    return await svc.get_unavailabilities(doctor_id, start, end)
