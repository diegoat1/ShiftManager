import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import RequireAdmin, get_shift_service
from app.schemas.common import PaginatedResponse
from app.schemas.shift import (
    GenerateShiftsRequest,
    ShiftCreate,
    ShiftLanguageRequirementCreate,
    ShiftRead,
    ShiftRequirementCreate,
    ShiftUpdate,
    TemplateCreate,
    TemplateRead,
)
from app.services.shift import ShiftService

router = APIRouter(prefix="/shifts", tags=["shifts"])

ShiftSvc = Annotated[ShiftService, Depends(get_shift_service)]


@router.post("/", response_model=ShiftRead, status_code=201)
async def create_shift(data: ShiftCreate, svc: ShiftSvc, admin: RequireAdmin):
    return await svc.create(data)


@router.get("/", response_model=PaginatedResponse[ShiftRead])
async def list_shifts(svc: ShiftSvc, skip: int = 0, limit: int = 50):
    items, total = await svc.get_all(skip=skip, limit=limit)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{shift_id}", response_model=ShiftRead)
async def get_shift(shift_id: uuid.UUID, svc: ShiftSvc):
    shift = await svc.get(shift_id)
    if not shift:
        raise HTTPException(404, "Shift not found")
    return shift


@router.patch("/{shift_id}", response_model=ShiftRead)
async def update_shift(shift_id: uuid.UUID, data: ShiftUpdate, svc: ShiftSvc, admin: RequireAdmin):
    shift = await svc.update(shift_id, data)
    if not shift:
        raise HTTPException(404, "Shift not found")
    return shift


@router.delete("/{shift_id}", status_code=204)
async def delete_shift(shift_id: uuid.UUID, svc: ShiftSvc, admin: RequireAdmin):
    if not await svc.delete(shift_id):
        raise HTTPException(404, "Shift not found")


@router.post("/{shift_id}/requirements", status_code=201)
async def add_requirement(shift_id: uuid.UUID, data: ShiftRequirementCreate, svc: ShiftSvc):
    return await svc.add_requirement(shift_id, data)


@router.post("/{shift_id}/language-requirements", status_code=201)
async def add_language_requirement(shift_id: uuid.UUID, data: ShiftLanguageRequirementCreate, svc: ShiftSvc):
    return await svc.add_language_requirement(shift_id, data)


# Calendar
@router.get("/calendar/{site_id}", response_model=list[ShiftRead])
async def get_calendar(
    site_id: uuid.UUID,
    svc: ShiftSvc,
    start: date = Query(...),
    end: date = Query(...),
):
    return await svc.get_calendar(site_id, start, end)


# Templates
@router.post("/templates", response_model=TemplateRead, status_code=201)
async def create_template(data: TemplateCreate, svc: ShiftSvc):
    return await svc.create_template(**data.model_dump())


@router.get("/templates/{site_id}", response_model=list[TemplateRead])
async def list_templates(site_id: uuid.UUID, svc: ShiftSvc):
    return await svc.get_templates(site_id)


@router.delete("/templates/item/{template_id}", status_code=204)
async def delete_template(template_id: uuid.UUID, svc: ShiftSvc, admin: RequireAdmin):
    if not await svc.delete_template(template_id):
        raise HTTPException(404, "Template not found")


@router.post("/generate", response_model=list[ShiftRead])
async def generate_shifts(data: GenerateShiftsRequest, svc: ShiftSvc, admin: RequireAdmin):
    return await svc.generate_shifts(data)
