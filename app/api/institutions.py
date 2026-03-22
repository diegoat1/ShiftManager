import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import RequireAdmin, get_institution_service
from app.schemas.common import PaginatedResponse
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionRead,
    InstitutionUpdate,
    LanguageRequirementCreate,
    LanguageRequirementRead,
    RequirementCreate,
    RequirementRead,
    SiteCreate,
    SiteRead,
    SiteUpdate,
)
from app.services.institution import InstitutionService

router = APIRouter(prefix="/institutions", tags=["institutions"])

InstSvc = Annotated[InstitutionService, Depends(get_institution_service)]


@router.post("/", response_model=InstitutionRead, status_code=201)
async def create_institution(data: InstitutionCreate, svc: InstSvc, admin: RequireAdmin):
    return await svc.create(data)


@router.get("/", response_model=PaginatedResponse[InstitutionRead])
async def list_institutions(svc: InstSvc, skip: int = 0, limit: int = 50):
    items, total = await svc.get_all(skip=skip, limit=limit)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/{institution_id}", response_model=InstitutionRead)
async def get_institution(institution_id: uuid.UUID, svc: InstSvc):
    inst = await svc.get(institution_id)
    if not inst:
        raise HTTPException(404, "Institution not found")
    return inst


@router.patch("/{institution_id}", response_model=InstitutionRead)
async def update_institution(institution_id: uuid.UUID, data: InstitutionUpdate, svc: InstSvc, admin: RequireAdmin):
    inst = await svc.update(institution_id, data)
    if not inst:
        raise HTTPException(404, "Institution not found")
    return inst


@router.delete("/{institution_id}", status_code=204)
async def delete_institution(institution_id: uuid.UUID, svc: InstSvc, admin: RequireAdmin):
    if not await svc.delete(institution_id):
        raise HTTPException(404, "Institution not found")


# Sites
@router.post("/{institution_id}/sites", response_model=SiteRead, status_code=201)
async def create_site(institution_id: uuid.UUID, data: SiteCreate, svc: InstSvc, admin: RequireAdmin):
    return await svc.create_site(institution_id, data)


@router.get("/{institution_id}/sites", response_model=list[SiteRead])
async def list_sites(institution_id: uuid.UUID, svc: InstSvc):
    return await svc.get_sites(institution_id)


@router.patch("/sites/{site_id}", response_model=SiteRead)
async def update_site(site_id: uuid.UUID, data: SiteUpdate, svc: InstSvc):
    site = await svc.update_site(site_id, data)
    if not site:
        raise HTTPException(404, "Site not found")
    return site


# Requirements
@router.post("/{institution_id}/requirements", response_model=RequirementRead, status_code=201)
async def add_requirement(institution_id: uuid.UUID, data: RequirementCreate, svc: InstSvc):
    return await svc.add_requirement(institution_id, data)


@router.get("/{institution_id}/requirements", response_model=list[RequirementRead])
async def list_requirements(institution_id: uuid.UUID, svc: InstSvc):
    return await svc.get_requirements(institution_id)


@router.post("/{institution_id}/language-requirements", response_model=LanguageRequirementRead, status_code=201)
async def add_language_requirement(institution_id: uuid.UUID, data: LanguageRequirementCreate, svc: InstSvc):
    return await svc.add_language_requirement(institution_id, data)


@router.get("/{institution_id}/language-requirements", response_model=list[LanguageRequirementRead])
async def list_language_requirements(institution_id: uuid.UUID, svc: InstSvc):
    return await svc.get_language_requirements(institution_id)
