import uuid
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.offer import ShiftOffer
from app.repositories.base import BaseRepository
from app.utils.enums import OfferStatus


class OfferRepository(BaseRepository[ShiftOffer]):
    def __init__(self, session: AsyncSession):
        super().__init__(ShiftOffer, session)

    async def get_by_shift(self, shift_id: uuid.UUID) -> list[ShiftOffer]:
        stmt = (
            select(ShiftOffer)
            .options(selectinload(ShiftOffer.doctor), selectinload(ShiftOffer.shift))
            .where(ShiftOffer.shift_id == shift_id)
            .order_by(ShiftOffer.rank_snapshot.asc().nullslast())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_doctor(self, doctor_id: uuid.UUID, status: OfferStatus | None = None) -> list[ShiftOffer]:
        stmt = (
            select(ShiftOffer)
            .options(selectinload(ShiftOffer.shift))
            .where(ShiftOffer.doctor_id == doctor_id)
        )
        if status:
            stmt = stmt.where(ShiftOffer.status == status)
        stmt = stmt.order_by(ShiftOffer.offered_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_by_doctor(self, doctor_id: uuid.UUID) -> list[ShiftOffer]:
        stmt = (
            select(ShiftOffer)
            .options(selectinload(ShiftOffer.shift))
            .where(
                ShiftOffer.doctor_id == doctor_id,
                ShiftOffer.status.in_([OfferStatus.PROPOSED, OfferStatus.VIEWED]),
            )
            .order_by(ShiftOffer.expires_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_expired(self) -> list[ShiftOffer]:
        now = datetime.utcnow()
        stmt = (
            select(ShiftOffer)
            .where(
                ShiftOffer.status.in_([OfferStatus.PROPOSED, OfferStatus.VIEWED]),
                ShiftOffer.expires_at != None,
                ShiftOffer.expires_at < now,
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_existing(self, shift_id: uuid.UUID, doctor_id: uuid.UUID) -> ShiftOffer | None:
        stmt = select(ShiftOffer).where(
            ShiftOffer.shift_id == shift_id,
            ShiftOffer.doctor_id == doctor_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_doctor(self, doctor_id: uuid.UUID, status: OfferStatus | None = None) -> int:
        stmt = select(func.count()).select_from(ShiftOffer).where(ShiftOffer.doctor_id == doctor_id)
        if status:
            stmt = stmt.where(ShiftOffer.status == status)
        result = await self.session.execute(stmt)
        return result.scalar_one()
