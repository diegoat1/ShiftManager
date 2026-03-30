import uuid
from datetime import date, datetime, timedelta
from typing import Sequence

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.assignment import ShiftAssignment
from app.models.institution import InstitutionSite
from app.models.shift import Shift
from app.repositories.base import BaseRepository
from app.utils.enums import AssignmentStatus


class AssignmentRepository(BaseRepository[ShiftAssignment]):
    def __init__(self, session: AsyncSession):
        super().__init__(ShiftAssignment, session)

    async def get_by_shift(self, shift_id: uuid.UUID) -> Sequence[ShiftAssignment]:
        result = await self.session.execute(
            select(ShiftAssignment).where(ShiftAssignment.shift_id == shift_id)
        )
        return result.scalars().all()

    async def get_by_doctor(
        self, doctor_id: uuid.UUID, start: datetime | None = None, end: datetime | None = None
    ) -> Sequence[ShiftAssignment]:
        stmt = (
            select(ShiftAssignment)
            .join(Shift)
            .where(
                ShiftAssignment.doctor_id == doctor_id,
                ShiftAssignment.status.in_([AssignmentStatus.PROPOSED, AssignmentStatus.CONFIRMED]),
            )
        )
        if start:
            stmt = stmt.where(Shift.start_datetime >= start)
        if end:
            stmt = stmt.where(Shift.end_datetime <= end)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_doctor_with_details(
        self,
        doctor_id: uuid.UUID,
        start: datetime | None = None,
        end: datetime | None = None,
        statuses: list[AssignmentStatus] | None = None,
        limit: int | None = None,
    ) -> Sequence[ShiftAssignment]:
        stmt = (
            select(ShiftAssignment)
            .join(Shift)
            .options(
                selectinload(ShiftAssignment.shift)
                .selectinload(Shift.site)
                .selectinload(InstitutionSite.institution)
            )
            .where(ShiftAssignment.doctor_id == doctor_id)
        )
        if statuses:
            stmt = stmt.where(ShiftAssignment.status.in_(statuses))
        if start:
            stmt = stmt.where(Shift.start_datetime >= start)
        if end:
            stmt = stmt.where(Shift.end_datetime <= end)
        stmt = stmt.order_by(Shift.start_datetime.asc())
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    async def get_existing(self, shift_id: uuid.UUID, doctor_id: uuid.UUID) -> ShiftAssignment | None:
        result = await self.session.execute(
            select(ShiftAssignment).where(
                ShiftAssignment.shift_id == shift_id,
                ShiftAssignment.doctor_id == doctor_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_active_for_shift(self, shift_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(ShiftAssignment).where(
                ShiftAssignment.shift_id == shift_id,
                ShiftAssignment.status.in_([AssignmentStatus.PROPOSED, AssignmentStatus.CONFIRMED]),
            )
        )
        return result.scalar_one()

    async def count_consecutive_days(self, doctor_id: uuid.UUID, target_date: date) -> int:
        """Count consecutive working days around target_date."""
        count = 0
        # Check backwards
        d = target_date - timedelta(days=1)
        while True:
            result = await self.session.execute(
                select(func.count()).select_from(ShiftAssignment)
                .join(Shift)
                .where(
                    ShiftAssignment.doctor_id == doctor_id,
                    ShiftAssignment.status.in_([AssignmentStatus.PROPOSED, AssignmentStatus.CONFIRMED]),
                    Shift.date == d,
                )
            )
            if result.scalar_one() == 0:
                break
            count += 1
            d -= timedelta(days=1)

        # Check forwards
        d = target_date + timedelta(days=1)
        while True:
            result = await self.session.execute(
                select(func.count()).select_from(ShiftAssignment)
                .join(Shift)
                .where(
                    ShiftAssignment.doctor_id == doctor_id,
                    ShiftAssignment.status.in_([AssignmentStatus.PROPOSED, AssignmentStatus.CONFIRMED]),
                    Shift.date == d,
                )
            )
            if result.scalar_one() == 0:
                break
            count += 1
            d += timedelta(days=1)

        return count + 1  # Include target_date itself

    async def count_shifts_in_month(self, doctor_id: uuid.UUID, year: int, month: int) -> int:
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        result = await self.session.execute(
            select(func.count()).select_from(ShiftAssignment)
            .join(Shift)
            .where(
                ShiftAssignment.doctor_id == doctor_id,
                ShiftAssignment.status.in_([AssignmentStatus.PROPOSED, AssignmentStatus.CONFIRMED]),
                Shift.date >= first_day,
                Shift.date <= last_day,
            )
        )
        return result.scalar_one()

    async def count_night_shifts_in_month(self, doctor_id: uuid.UUID, year: int, month: int) -> int:
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        result = await self.session.execute(
            select(func.count()).select_from(ShiftAssignment)
            .join(Shift)
            .where(
                ShiftAssignment.doctor_id == doctor_id,
                ShiftAssignment.status.in_([AssignmentStatus.PROPOSED, AssignmentStatus.CONFIRMED]),
                Shift.date >= first_day,
                Shift.date <= last_day,
                Shift.is_night == True,
            )
        )
        return result.scalar_one()
