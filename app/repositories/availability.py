import uuid
from datetime import date, time
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.availability import DoctorAvailability, DoctorUnavailability
from app.repositories.base import BaseRepository


class AvailabilityRepository(BaseRepository[DoctorAvailability]):
    def __init__(self, session: AsyncSession):
        super().__init__(DoctorAvailability, session)

    async def is_available(self, doctor_id: uuid.UUID, target_date: date, start: time, end: time) -> bool:
        # Check no unavailability covering this date
        unav = await self.session.execute(
            select(DoctorUnavailability).where(
                DoctorUnavailability.doctor_id == doctor_id,
                DoctorUnavailability.start_date <= target_date,
                DoctorUnavailability.end_date >= target_date,
                DoctorUnavailability.is_approved == True,
            )
        )
        if unav.scalars().first():
            return False

        # Check positive availability exists covering the time
        avail = await self.session.execute(
            select(DoctorAvailability).where(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.date == target_date,
                DoctorAvailability.start_time <= start,
                DoctorAvailability.end_time >= end,
            )
        )
        return avail.scalars().first() is not None

    async def get_availability_with_type(
        self, doctor_id: uuid.UUID, target_date: date, start: time, end: time
    ) -> DoctorAvailability | None:
        result = await self.session.execute(
            select(DoctorAvailability).where(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.date == target_date,
                DoctorAvailability.start_time <= start,
                DoctorAvailability.end_time >= end,
            )
        )
        return result.scalars().first()

    async def get_by_doctor_and_date_range(
        self, doctor_id: uuid.UUID, start: date, end: date
    ) -> Sequence[DoctorAvailability]:
        result = await self.session.execute(
            select(DoctorAvailability).where(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.date >= start,
                DoctorAvailability.date <= end,
            )
        )
        return result.scalars().all()

    async def bulk_create(self, doctor_id: uuid.UUID, entries: list[dict]) -> list[DoctorAvailability]:
        created = []
        for entry in entries:
            avail = DoctorAvailability(doctor_id=doctor_id, **entry)
            self.session.add(avail)
            created.append(avail)
        await self.session.flush()
        return created

    # Unavailability
    async def get_unavailability_by_id(self, id: int) -> DoctorUnavailability | None:
        return await self.session.get(DoctorUnavailability, id)

    async def create_unavailability(self, doctor_id: uuid.UUID, **kwargs) -> DoctorUnavailability:
        unav = DoctorUnavailability(doctor_id=doctor_id, **kwargs)
        self.session.add(unav)
        await self.session.flush()
        await self.session.refresh(unav)
        return unav

    async def get_unavailabilities(
        self, doctor_id: uuid.UUID, start: date | None = None, end: date | None = None
    ) -> Sequence[DoctorUnavailability]:
        stmt = select(DoctorUnavailability).where(DoctorUnavailability.doctor_id == doctor_id)
        if start:
            stmt = stmt.where(DoctorUnavailability.end_date >= start)
        if end:
            stmt = stmt.where(DoctorUnavailability.start_date <= end)
        result = await self.session.execute(stmt)
        return result.scalars().all()
