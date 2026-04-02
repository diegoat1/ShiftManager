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

    async def get_shift_ids_for_doctor(
        self,
        doctor_id: uuid.UUID,
        shift_ids: list[uuid.UUID],
    ) -> set[uuid.UUID]:
        """Return shift_ids where any assignment exists for doctor, regardless of status.

        Replicates the semantics of get_existing() — used for already_applied checks.
        """
        if not shift_ids:
            return set()
        result = await self.session.execute(
            select(ShiftAssignment.shift_id).where(
                ShiftAssignment.doctor_id == doctor_id,
                ShiftAssignment.shift_id.in_(shift_ids),
            )
        )
        return set(result.scalars().all())

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

    async def bulk_nearby_shifts_data(
        self,
        doctor_ids: list[uuid.UUID],
        window_start: datetime,
        window_end: datetime,
    ) -> dict[uuid.UUID, list[tuple]]:
        """Return dict[doctor_id -> list[(shift_id, date, start_datetime, end_datetime, site_id)]]."""
        if not doctor_ids:
            return {}

        stmt = (
            select(
                ShiftAssignment.doctor_id,
                Shift.id,
                Shift.date,
                Shift.start_datetime,
                Shift.end_datetime,
                Shift.site_id,
            )
            .join(Shift, ShiftAssignment.shift_id == Shift.id)
            .where(
                ShiftAssignment.doctor_id.in_(doctor_ids),
                Shift.start_datetime >= window_start,
                Shift.end_datetime <= window_end,
            )
        )
        result = await self.session.execute(stmt)
        out: dict[uuid.UUID, list[tuple]] = {did: [] for did in doctor_ids}
        for row in result.all():
            out[row[0]].append((row[1], row[2], row[3], row[4], row[5]))
        return out

    async def bulk_consecutive_days(
        self,
        doctor_ids: list[uuid.UUID],
        target_date: date,
        lookback_days: int = 14,
    ) -> dict[uuid.UUID, int]:
        """Count consecutive working days around target_date for each doctor (pure Python after 1 query)."""
        if not doctor_ids:
            return {}

        window_start = target_date - timedelta(days=lookback_days)
        window_end = target_date + timedelta(days=lookback_days)

        result = await self.session.execute(
            select(ShiftAssignment.doctor_id, Shift.date)
            .join(Shift, ShiftAssignment.shift_id == Shift.id)
            .where(
                ShiftAssignment.doctor_id.in_(doctor_ids),
                ShiftAssignment.status.in_([AssignmentStatus.PROPOSED, AssignmentStatus.CONFIRMED]),
                Shift.date >= window_start,
                Shift.date <= window_end,
            )
            .distinct()
        )
        days_by_doctor: dict[uuid.UUID, set[date]] = {did: set() for did in doctor_ids}
        for row in result.all():
            days_by_doctor[row.doctor_id].add(row.date)

        out: dict[uuid.UUID, int] = {}
        for did in doctor_ids:
            worked = days_by_doctor[did]
            count = 1  # target_date itself
            d = target_date - timedelta(days=1)
            while d in worked:
                count += 1
                d -= timedelta(days=1)
            d = target_date + timedelta(days=1)
            while d in worked:
                count += 1
                d += timedelta(days=1)
            out[did] = count
        return out

    async def bulk_shifts_in_month(
        self,
        doctor_ids: list[uuid.UUID],
        year: int,
        month: int,
    ) -> dict[uuid.UUID, int]:
        if not doctor_ids:
            return {}

        first_day = date(year, month, 1)
        next_month_year = year + 1 if month == 12 else year
        next_month = (month % 12) + 1
        last_day = date(next_month_year, next_month, 1) - timedelta(days=1)

        result = await self.session.execute(
            select(ShiftAssignment.doctor_id, func.count().label("cnt"))
            .join(Shift, ShiftAssignment.shift_id == Shift.id)
            .where(
                ShiftAssignment.doctor_id.in_(doctor_ids),
                ShiftAssignment.status.in_([AssignmentStatus.PROPOSED, AssignmentStatus.CONFIRMED]),
                Shift.date >= first_day,
                Shift.date <= last_day,
            )
            .group_by(ShiftAssignment.doctor_id)
        )
        counts = {did: 0 for did in doctor_ids}
        for row in result.all():
            counts[row.doctor_id] = row.cnt
        return counts

    async def bulk_night_shifts_in_month(
        self,
        doctor_ids: list[uuid.UUID],
        year: int,
        month: int,
    ) -> dict[uuid.UUID, int]:
        if not doctor_ids:
            return {}

        first_day = date(year, month, 1)
        next_month_year = year + 1 if month == 12 else year
        next_month = (month % 12) + 1
        last_day = date(next_month_year, next_month, 1) - timedelta(days=1)

        result = await self.session.execute(
            select(ShiftAssignment.doctor_id, func.count().label("cnt"))
            .join(Shift, ShiftAssignment.shift_id == Shift.id)
            .where(
                ShiftAssignment.doctor_id.in_(doctor_ids),
                ShiftAssignment.status.in_([AssignmentStatus.PROPOSED, AssignmentStatus.CONFIRMED]),
                Shift.date >= first_day,
                Shift.date <= last_day,
                Shift.is_night == True,  # noqa: E712
            )
            .group_by(ShiftAssignment.doctor_id)
        )
        counts = {did: 0 for did in doctor_ids}
        for row in result.all():
            counts[row.doctor_id] = row.cnt
        return counts

    async def get_worked_dates_for_doctor(
        self,
        doctor_id: uuid.UUID,
        start: date,
        end: date,
    ) -> set[date]:
        """Distinct dates the doctor has PROPOSED|CONFIRMED shifts in [start, end]."""
        result = await self.session.execute(
            select(Shift.date).distinct()
            .join(ShiftAssignment, ShiftAssignment.shift_id == Shift.id)
            .where(
                ShiftAssignment.doctor_id == doctor_id,
                ShiftAssignment.status.in_([AssignmentStatus.PROPOSED, AssignmentStatus.CONFIRMED]),
                Shift.date >= start,
                Shift.date <= end,
            )
        )
        return set(result.scalars().all())

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
