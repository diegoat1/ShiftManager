import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.availability import AvailabilityRepository
from app.schemas.availability import AvailabilityCreate, BulkAvailabilityCreate, UnavailabilityCreate


class AvailabilityService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AvailabilityRepository(session)

    async def set_availability(self, doctor_id: uuid.UUID, data: AvailabilityCreate):
        avail = await self.repo.create(
            doctor_id=doctor_id,
            date=data.date,
            start_time=data.start_time,
            end_time=data.end_time,
            availability_type=data.availability_type,
        )

        return avail

    async def bulk_set_availability(self, doctor_id: uuid.UUID, data: BulkAvailabilityCreate):
        entries = [e.model_dump() for e in data.entries]
        result = await self.repo.bulk_create(doctor_id, entries)

        return result

    async def get_availability(self, doctor_id: uuid.UUID, start: date, end: date):
        return await self.repo.get_by_doctor_and_date_range(doctor_id, start, end)

    async def create_unavailability(self, doctor_id: uuid.UUID, data: UnavailabilityCreate):
        unav = await self.repo.create_unavailability(
            doctor_id,
            start_date=data.start_date,
            end_date=data.end_date,
            reason=data.reason,
        )

        return unav

    async def get_unavailabilities(self, doctor_id: uuid.UUID, start: date | None = None, end: date | None = None):
        return await self.repo.get_unavailabilities(doctor_id, start, end)

    async def delete_availability(self, doctor_id: uuid.UUID, availability_id: int) -> bool:
        avail = await self.repo.get_by_id(availability_id)
        if not avail or avail.doctor_id != doctor_id:
            return False
        await self.repo.delete(avail)

        return True

    async def delete_unavailability(self, doctor_id: uuid.UUID, unavailability_id: int) -> bool:
        unav = await self.repo.get_unavailability_by_id(unavailability_id)
        if not unav or unav.doctor_id != doctor_id:
            return False
        await self.session.delete(unav)
        await self.session.flush()

        return True
