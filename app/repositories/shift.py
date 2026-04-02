import uuid
from datetime import date, datetime
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.institution import InstitutionSite
from app.models.shift import Shift, ShiftLanguageRequirement, ShiftRequirement, ShiftTemplate
from app.repositories.base import BaseRepository
from app.utils.enums import ShiftStatus


class ShiftRepository(BaseRepository[Shift]):
    def __init__(self, session: AsyncSession):
        super().__init__(Shift, session)

    async def get_with_requirements(self, shift_id: uuid.UUID) -> Shift | None:
        stmt = (
            select(Shift)
            .options(
                selectinload(Shift.requirements).selectinload(ShiftRequirement.certification_type),
                selectinload(Shift.language_requirements).selectinload(ShiftLanguageRequirement.language),
                selectinload(Shift.site),
            )
            .where(Shift.id == shift_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_shifts_by_date_range(
        self, site_id: uuid.UUID, start: date, end: date
    ) -> Sequence[Shift]:
        stmt = select(Shift).where(
            Shift.site_id == site_id,
            Shift.date >= start,
            Shift.date <= end,
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_unassigned_shifts(self, site_id: uuid.UUID | None = None) -> Sequence[Shift]:
        stmt = select(Shift).where(Shift.status.in_([ShiftStatus.OPEN, ShiftStatus.PARTIALLY_FILLED]))
        if site_id:
            stmt = stmt.where(Shift.site_id == site_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_doctor_shifts(
        self, doctor_id: uuid.UUID, start: datetime | None = None, end: datetime | None = None
    ) -> Sequence[Shift]:
        from app.models.assignment import ShiftAssignment
        stmt = (
            select(Shift)
            .join(ShiftAssignment)
            .where(ShiftAssignment.doctor_id == doctor_id)
        )
        if start:
            stmt = stmt.where(Shift.start_datetime >= start)
        if end:
            stmt = stmt.where(Shift.end_datetime <= end)
        stmt = stmt.order_by(Shift.start_datetime)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_recent_site_affinity_for_doctor(
        self,
        doctor_id: uuid.UUID,
        since: datetime,
    ) -> tuple[set[uuid.UUID], set[uuid.UUID]]:
        """Return (recent_site_ids, recent_institution_ids) for doctor's shifts since `since`.

        No assignment status filter — preserves get_doctor_shifts() semantics
        (CANCELLED assignments still count toward site affinity).
        1 query.
        """
        from app.models.assignment import ShiftAssignment

        stmt = (
            select(Shift.site_id, InstitutionSite.institution_id)
            .join(ShiftAssignment, ShiftAssignment.shift_id == Shift.id)
            .join(InstitutionSite, Shift.site_id == InstitutionSite.id)
            .where(
                ShiftAssignment.doctor_id == doctor_id,
                Shift.start_datetime >= since,
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        site_ids = {row[0] for row in rows}
        inst_ids = {row[1] for row in rows}
        return site_ids, inst_ids

    async def bulk_get_recent_site_affinity_for_doctors(
        self,
        doctor_ids: list[uuid.UUID],
        since: datetime,
    ) -> dict[uuid.UUID, tuple[set[uuid.UUID], set[uuid.UUID]]]:
        """Return dict[doctor_id -> (recent_site_ids, recent_institution_ids)].

        No assignment status filter — preserves get_doctor_shifts() semantics.
        1 query for all N doctors.
        """
        if not doctor_ids:
            return {}
        from app.models.assignment import ShiftAssignment

        stmt = (
            select(ShiftAssignment.doctor_id, Shift.site_id, InstitutionSite.institution_id)
            .join(ShiftAssignment, ShiftAssignment.shift_id == Shift.id)
            .join(InstitutionSite, Shift.site_id == InstitutionSite.id)
            .where(
                ShiftAssignment.doctor_id.in_(doctor_ids),
                Shift.start_datetime >= since,
            )
            .distinct()
        )
        result = await self.session.execute(stmt)

        out: dict[uuid.UUID, tuple[set[uuid.UUID], set[uuid.UUID]]] = {
            did: (set(), set()) for did in doctor_ids
        }
        for row in result.all():
            out[row[0]][0].add(row[1])  # site_id
            out[row[0]][1].add(row[2])  # institution_id
        return out

    async def add_requirement(self, shift_id: uuid.UUID, **kwargs) -> ShiftRequirement:
        req = ShiftRequirement(shift_id=shift_id, **kwargs)
        self.session.add(req)
        await self.session.flush()
        return req

    async def add_language_requirement(self, shift_id: uuid.UUID, **kwargs) -> ShiftLanguageRequirement:
        req = ShiftLanguageRequirement(shift_id=shift_id, **kwargs)
        self.session.add(req)
        await self.session.flush()
        return req

    # Templates
    async def create_template(self, **kwargs) -> ShiftTemplate:
        tmpl = ShiftTemplate(**kwargs)
        self.session.add(tmpl)
        await self.session.flush()
        await self.session.refresh(tmpl)
        return tmpl

    async def get_template(self, template_id: uuid.UUID) -> ShiftTemplate | None:
        return await self.session.get(ShiftTemplate, template_id)

    async def get_templates_by_site(self, site_id: uuid.UUID) -> Sequence[ShiftTemplate]:
        result = await self.session.execute(
            select(ShiftTemplate).where(ShiftTemplate.site_id == site_id)
        )
        return result.scalars().all()
