import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import DbSession, RequireAdmin, get_cooperative_assignment_service
from app.repositories.cooperative import CooperativeRepository
from app.schemas.cooperative import (
    CooperativeBrief, CooperativeCreate, CooperativeRead, CooperativeUpdate,
    SiteAssignmentCreate, SiteAssignmentRead, SiteAssignmentUpdate,
)
from app.services.cooperative_assignment import CooperativeSiteAssignmentService

router = APIRouter(prefix="/cooperatives", tags=["cooperatives"])


async def get_repo(session: DbSession) -> CooperativeRepository:
    return CooperativeRepository(session)


Repo = Annotated[CooperativeRepository, Depends(get_repo)]


@router.get("/", response_model=list[CooperativeBrief])
async def list_cooperatives(repo: Repo, search: str | None = None, skip: int = 0, limit: int = 200):
    return await repo.get_all(skip=skip, limit=limit, search=search)


@router.post("/", response_model=CooperativeRead, status_code=201)
async def create_cooperative(data: CooperativeCreate, repo: Repo, admin: RequireAdmin):
    return await repo.create(data)


@router.get("/{coop_id}", response_model=CooperativeRead)
async def get_cooperative(coop_id: uuid.UUID, repo: Repo):
    coop = await repo.get_by_id(coop_id)
    if not coop:
        raise HTTPException(404, "Cooperative not found")
    return coop


@router.patch("/{coop_id}", response_model=CooperativeRead)
async def update_cooperative(coop_id: uuid.UUID, data: CooperativeUpdate, repo: Repo, admin: RequireAdmin):
    coop = await repo.get_by_id(coop_id)
    if not coop:
        raise HTTPException(404, "Cooperative not found")
    return await repo.update(coop, data)


@router.delete("/{coop_id}", status_code=204)
async def delete_cooperative(coop_id: uuid.UUID, repo: Repo, admin: RequireAdmin):
    coop = await repo.get_by_id(coop_id)
    if not coop:
        raise HTTPException(404, "Cooperative not found")
    await repo.delete(coop)


# --- Site assignments ---

AssignmentSvc = Annotated[CooperativeSiteAssignmentService, Depends(get_cooperative_assignment_service)]


@router.post("/{coop_id}/sites", response_model=SiteAssignmentRead, status_code=201)
async def assign_site(coop_id: uuid.UUID, data: SiteAssignmentCreate, svc: AssignmentSvc, admin: RequireAdmin):
    try:
        return await svc.assign(
            cooperative_id=coop_id,
            site_id=data.site_id,
            start_date=data.start_date,
            end_date=data.end_date,
            notes=data.notes,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/{coop_id}/sites", response_model=list[SiteAssignmentRead])
async def list_site_assignments(coop_id: uuid.UUID, svc: AssignmentSvc, active_only: bool = True):
    return await svc.get_sites_for_cooperative(coop_id, active_only=active_only)


@router.patch("/{coop_id}/sites/{assignment_id}", response_model=SiteAssignmentRead)
async def update_site_assignment(
    coop_id: uuid.UUID, assignment_id: uuid.UUID,
    data: SiteAssignmentUpdate, svc: AssignmentSvc, admin: RequireAdmin,
):
    # Validate assignment belongs to this cooperative
    from app.repositories.cooperative import CooperativeRepository
    repo = CooperativeRepository(svc.session)
    assignment = await repo.get_assignment(assignment_id)
    if not assignment or assignment.cooperative_id != coop_id:
        raise HTTPException(404, "Assignment not found for this cooperative")
    try:
        return await svc.update(
            assignment_id,
            end_date=data.end_date if data.end_date is not None else ...,
            notes=data.notes if data.notes is not None else ...,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
