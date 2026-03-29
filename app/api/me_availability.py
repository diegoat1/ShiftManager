from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import CurrentDoctor, get_availability_service
from app.models.doctor import Doctor
from app.schemas.availability import (
    AvailabilityCreate,
    AvailabilityRead,
    BulkAvailabilityCreate,
    UnavailabilityCreate,
    UnavailabilityRead,
)
from app.services.availability import AvailabilityService

router = APIRouter(prefix="/me", tags=["me-availability"])

AvailSvc = Annotated[AvailabilityService, Depends(get_availability_service)]


@router.get("/availability", response_model=list[AvailabilityRead])
async def get_my_availability(
    doctor: CurrentDoctor,
    svc: AvailSvc,
    start: date = Query(...),
    end: date = Query(...),
):
    return await svc.get_availability(doctor.id, start, end)


@router.post("/availability", response_model=AvailabilityRead, status_code=201)
async def create_my_availability(data: AvailabilityCreate, doctor: CurrentDoctor, svc: AvailSvc):
    return await svc.set_availability(doctor.id, data)


@router.post("/availability/bulk", status_code=201)
async def bulk_create_my_availability(data: BulkAvailabilityCreate, doctor: CurrentDoctor, svc: AvailSvc):
    return await svc.bulk_set_availability(doctor.id, data)


@router.delete("/availability/{availability_id}", status_code=204)
async def delete_my_availability(availability_id: int, doctor: CurrentDoctor, svc: AvailSvc):
    if not await svc.delete_availability(doctor.id, availability_id):
        raise HTTPException(404, "Availability entry not found")


@router.get("/unavailability", response_model=list[UnavailabilityRead])
async def get_my_unavailability(
    doctor: CurrentDoctor,
    svc: AvailSvc,
    start: date | None = None,
    end: date | None = None,
):
    return await svc.get_unavailabilities(doctor.id, start, end)


@router.post("/unavailability", response_model=UnavailabilityRead, status_code=201)
async def create_my_unavailability(data: UnavailabilityCreate, doctor: CurrentDoctor, svc: AvailSvc):
    return await svc.create_unavailability(doctor.id, data)


@router.delete("/unavailability/{unavailability_id}", status_code=204)
async def delete_my_unavailability(unavailability_id: int, doctor: CurrentDoctor, svc: AvailSvc):
    if not await svc.delete_unavailability(doctor.id, unavailability_id):
        raise HTTPException(404, "Unavailability entry not found")
