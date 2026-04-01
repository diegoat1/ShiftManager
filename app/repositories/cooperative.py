import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cooperative import Cooperative
from app.repositories.base import BaseRepository
from app.schemas.cooperative import CooperativeCreate, CooperativeUpdate


class CooperativeRepository(BaseRepository[Cooperative]):
    def __init__(self, session: AsyncSession):
        super().__init__(Cooperative, session)

    async def get_all(self, skip: int = 0, limit: int = 200, search: str | None = None, **filters):
        stmt = select(Cooperative)
        if search:
            q = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Cooperative.name.ilike(q),
                    Cooperative.partita_iva.ilike(q),
                    Cooperative.city.ilike(q),
                )
            )
        stmt = stmt.order_by(Cooperative.name).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, search: str | None = None, **filters) -> int:
        stmt = select(func.count()).select_from(Cooperative)
        if search:
            q = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Cooperative.name.ilike(q),
                    Cooperative.partita_iva.ilike(q),
                    Cooperative.city.ilike(q),
                )
            )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_partita_iva(self, partita_iva: str) -> Cooperative | None:
        result = await self.session.execute(
            select(Cooperative).where(Cooperative.partita_iva == partita_iva)
        )
        return result.scalar_one_or_none()

    async def create(self, data: CooperativeCreate) -> Cooperative:
        coop = Cooperative(**data.model_dump())
        self.session.add(coop)
        await self.session.flush()
        await self.session.refresh(coop)
        return coop

    async def update(self, coop: Cooperative, data: CooperativeUpdate) -> Cooperative:
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(coop, k, v)
        await self.session.flush()
        await self.session.refresh(coop)
        return coop

    async def delete(self, coop: Cooperative) -> None:
        await self.session.delete(coop)
        await self.session.flush()
