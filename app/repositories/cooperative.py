import uuid
from datetime import date

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cooperative import Cooperative, CooperativeSiteAssignment
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

    # --- Site assignments ---

    async def create_assignment(self, **kwargs) -> CooperativeSiteAssignment:
        assignment = CooperativeSiteAssignment(**kwargs)
        self.session.add(assignment)
        await self.session.flush()
        await self.session.refresh(assignment)
        return assignment

    async def get_assignment(self, assignment_id: uuid.UUID) -> CooperativeSiteAssignment | None:
        return await self.session.get(CooperativeSiteAssignment, assignment_id)

    async def get_active_for_site(self, site_id: uuid.UUID) -> CooperativeSiteAssignment | None:
        """Return the current (ongoing) assignment for a site, or None."""
        result = await self.session.execute(
            select(CooperativeSiteAssignment).where(
                CooperativeSiteAssignment.site_id == site_id,
                CooperativeSiteAssignment.end_date.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_assignments_for_cooperative(
        self, cooperative_id: uuid.UUID, active_only: bool = True
    ) -> list[CooperativeSiteAssignment]:
        stmt = select(CooperativeSiteAssignment).where(
            CooperativeSiteAssignment.cooperative_id == cooperative_id
        )
        if active_only:
            stmt = stmt.where(CooperativeSiteAssignment.end_date.is_(None))
        stmt = stmt.order_by(CooperativeSiteAssignment.start_date.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_history_for_site(self, site_id: uuid.UUID) -> list[CooperativeSiteAssignment]:
        result = await self.session.execute(
            select(CooperativeSiteAssignment)
            .where(CooperativeSiteAssignment.site_id == site_id)
            .order_by(CooperativeSiteAssignment.start_date.desc())
        )
        return list(result.scalars().all())

    async def check_overlap(
        self,
        site_id: uuid.UUID,
        start_date: date,
        end_date: date | None,
        exclude_id: uuid.UUID | None = None,
    ) -> CooperativeSiteAssignment | None:
        """Return the first overlapping assignment, or None."""
        effective_end = end_date if end_date is not None else date(9999, 12, 31)
        stmt = select(CooperativeSiteAssignment).where(
            CooperativeSiteAssignment.site_id == site_id,
            CooperativeSiteAssignment.start_date <= effective_end,
            or_(
                CooperativeSiteAssignment.end_date.is_(None),
                CooperativeSiteAssignment.end_date >= start_date,
            ),
        )
        if exclude_id:
            stmt = stmt.where(CooperativeSiteAssignment.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()
