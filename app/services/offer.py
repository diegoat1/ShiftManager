import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.offer import ShiftOffer
from app.repositories.offer import OfferRepository
from app.repositories.shift import ShiftRepository
from app.services.assignment import AssignmentService
from app.schemas.assignment import AssignmentCreate
from app.utils.enums import AssignmentStatus, OfferStatus, ShiftStatus


class OfferService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = OfferRepository(session)
        self.shift_repo = ShiftRepository(session)

    async def send_offer(
        self,
        shift_id: uuid.UUID,
        doctor_id: uuid.UUID,
        expires_in_hours: float = 12.0,
        rank: int | None = None,
        score: int | None = None,
        proposed_by: uuid.UUID | None = None,
    ) -> ShiftOffer:
        existing = await self.repo.get_existing(shift_id, doctor_id)
        if existing:
            raise ValueError("Offer already exists for this doctor and shift")

        offer = await self.repo.create(
            shift_id=shift_id,
            doctor_id=doctor_id,
            status=OfferStatus.PROPOSED,
            offered_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours),
            rank_snapshot=rank,
            score_snapshot=score,
            proposed_by=proposed_by,
        )

        # Update shift status
        shift = await self.shift_repo.get_by_id(shift_id)
        if shift and shift.status == ShiftStatus.OPEN:
            await self.shift_repo.update(shift, status=ShiftStatus.PROPOSING)

        await self.session.commit()
        return offer

    async def send_batch(
        self,
        shift_id: uuid.UUID,
        doctor_ids: list[uuid.UUID],
        expires_in_hours: float = 12.0,
        ranks: dict[uuid.UUID, int] | None = None,
        scores: dict[uuid.UUID, int] | None = None,
        proposed_by: uuid.UUID | None = None,
    ) -> list[ShiftOffer]:
        offers = []
        for doctor_id in doctor_ids:
            try:
                rank = ranks.get(doctor_id) if ranks else None
                score = scores.get(doctor_id) if scores else None
                offer = await self.send_offer(
                    shift_id, doctor_id, expires_in_hours, rank, score, proposed_by
                )
                offers.append(offer)
            except ValueError:
                continue
        return offers

    async def accept(self, offer_id: uuid.UUID) -> ShiftOffer | None:
        offer = await self.repo.get_by_id(offer_id)
        if not offer:
            return None
        if offer.status not in (OfferStatus.PROPOSED, OfferStatus.VIEWED):
            raise ValueError(f"Cannot accept offer in status {offer.status}")

        offer.status = OfferStatus.ACCEPTED
        offer.responded_at = datetime.utcnow()
        await self.session.flush()

        # Auto-create assignment
        assignment_svc = AssignmentService(self.session)
        assignment, _ = await assignment_svc.assign(
            AssignmentCreate(shift_id=offer.shift_id, doctor_id=offer.doctor_id)
        )

        await self.session.commit()
        return offer

    async def reject(self, offer_id: uuid.UUID, response_note: str | None = None) -> ShiftOffer | None:
        offer = await self.repo.get_by_id(offer_id)
        if not offer:
            return None
        if offer.status not in (OfferStatus.PROPOSED, OfferStatus.VIEWED):
            raise ValueError(f"Cannot reject offer in status {offer.status}")

        offer.status = OfferStatus.REJECTED
        offer.responded_at = datetime.utcnow()
        offer.response_note = response_note
        await self.session.flush()
        await self.session.commit()
        return offer

    async def cancel(self, offer_id: uuid.UUID) -> ShiftOffer | None:
        offer = await self.repo.get_by_id(offer_id)
        if not offer:
            return None
        if offer.status not in (OfferStatus.PROPOSED, OfferStatus.VIEWED):
            raise ValueError(f"Cannot cancel offer in status {offer.status}")

        offer.status = OfferStatus.CANCELLED
        await self.session.flush()
        await self.session.commit()
        return offer

    async def expire_stale(self) -> int:
        expired = await self.repo.get_expired()
        for offer in expired:
            offer.status = OfferStatus.EXPIRED
        await self.session.flush()

        # Check if any shifts need to go back to open/uncovered
        shift_ids = {o.shift_id for o in expired}
        for shift_id in shift_ids:
            remaining = await self.repo.get_by_shift(shift_id)
            active = [o for o in remaining if o.status in (OfferStatus.PROPOSED, OfferStatus.VIEWED)]
            if not active:
                shift = await self.shift_repo.get_by_id(shift_id)
                if shift and shift.status == ShiftStatus.PROPOSING:
                    await self.shift_repo.update(shift, status=ShiftStatus.UNCOVERED)

        await self.session.commit()
        return len(expired)

    async def get_by_shift(self, shift_id: uuid.UUID) -> list[ShiftOffer]:
        return await self.repo.get_by_shift(shift_id)

    async def get_by_doctor(self, doctor_id: uuid.UUID) -> list[ShiftOffer]:
        return await self.repo.get_by_doctor(doctor_id)

    async def get_pending_by_doctor(self, doctor_id: uuid.UUID) -> list[ShiftOffer]:
        return await self.repo.get_pending_by_doctor(doctor_id)
