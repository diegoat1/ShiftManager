import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import DbSession, RequireAdmin
from app.repositories.cooperative import CooperativeRepository
from app.schemas.cooperative import CooperativeBrief, CooperativeCreate, CooperativeRead, CooperativeUpdate

router = APIRouter(prefix="/cooperatives", tags=["cooperatives"])


async def get_repo(session: DbSession) -> CooperativeRepository:
    return CooperativeRepository(session)


Repo = Annotated[CooperativeRepository, Depends(get_repo)]


@router.get("/", response_model=list[CooperativeBrief])
async def list_cooperatives(repo: Repo, search: str | None = None, skip: int = 0, limit: int = 200):
    return await repo.get_all(skip=skip, limit=limit, search=search)


@router.post("/", response_model=CooperativeRead, status_code=201)
async def create_cooperative(data: CooperativeCreate, repo: Repo, admin: RequireAdmin):
    from app.models.cooperative import Cooperative
    coop = Cooperative(**data.model_dump())
    repo.session.add(coop)
    await repo.session.flush()
    await repo.session.refresh(coop)
    return coop


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
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(coop, k, v)
    await repo.session.flush()
    await repo.session.refresh(coop)
    return coop


@router.delete("/{coop_id}", status_code=204)
async def delete_cooperative(coop_id: uuid.UUID, repo: Repo, admin: RequireAdmin):
    coop = await repo.get_by_id(coop_id)
    if not coop:
        raise HTTPException(404, "Cooperative not found")
    await repo.session.delete(coop)
