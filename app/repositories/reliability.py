import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reliability import DoctorReliabilityStats
from app.repositories.base import BaseRepository


class ReliabilityRepository(BaseRepository[DoctorReliabilityStats]):
    def __init__(self, session: AsyncSession):
        super().__init__(DoctorReliabilityStats, session)

    async def get_by_doctor(self, doctor_id: uuid.UUID) -> DoctorReliabilityStats | None:
        stmt = select(DoctorReliabilityStats).where(
            DoctorReliabilityStats.doctor_id == doctor_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_stats(self, skip: int = 0, limit: int = 50) -> list[DoctorReliabilityStats]:
        stmt = (
            select(DoctorReliabilityStats)
            .order_by(DoctorReliabilityStats.reliability_score.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
