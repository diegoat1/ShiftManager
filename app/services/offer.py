import uuid
from datetime import timedelta

from app.utils.dates import utcnow_naive

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
            offered_at=utcnow_naive(),
            expires_at=utcnow_naive() + timedelta(hours=expires_in_hours),
            rank_snapshot=rank,
            score_snapshot=score,
            proposed_by=proposed_by,
        )

        # Update shift status
        shift = await self.shift_repo.get_by_id(shift_id)
        if shift and shift.status == ShiftStatus.OPEN:
            await self.shift_repo.update(shift, status=ShiftStatus.PROPOSING)

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
        if not doctor_ids:
            return []

        now = utcnow_naive()
        expires_at = now + timedelta(hours=expires_in_hours)

        # One query: find doctors that already have an offer for this shift
        already_offered = await self.repo.get_existing_for_doctors(shift_id, doctor_ids)
        new_ids = [did for did in doctor_ids if did not in already_offered]

        if not new_ids:
            return []

        # Build all offer objects and insert in one statement
        offers = [
            ShiftOffer(
                shift_id=shift_id,
                doctor_id=did,
                status=OfferStatus.PROPOSED,
                offered_at=now,
                expires_at=expires_at,
                rank_snapshot=ranks.get(did) if ranks else None,
                score_snapshot=scores.get(did) if scores else None,
                proposed_by=proposed_by,
            )
            for did in new_ids
        ]
        self.session.add_all(offers)
        await self.session.flush()

        # Update shift status once
        shift = await self.shift_repo.get_by_id(shift_id)
        if shift and shift.status == ShiftStatus.OPEN:
            await self.shift_repo.update(shift, status=ShiftStatus.PROPOSING)

        return offers

    async def accept(self, offer_id: uuid.UUID) -> ShiftOffer | None:
        offer = await self.repo.get_by_id(offer_id)
        if not offer:
            return None
        if offer.status not in (OfferStatus.PROPOSED, OfferStatus.VIEWED):
            raise ValueError(f"Cannot accept offer in status {offer.status}")

        offer.status = OfferStatus.ACCEPTED
        offer.responded_at = utcnow_naive()
        await self.session.flush()

        # Auto-create assignment — must succeed or we roll back the offer status change
        assignment_svc = AssignmentService(self.session)
        assignment, result = await assignment_svc.assign(
            AssignmentCreate(shift_id=offer.shift_id, doctor_id=offer.doctor_id)
        )
        if assignment is None:
            raise ValueError(f"Doctor is not eligible for this shift: {'; '.join(result.reasons)}")

        return offer

    async def reject(self, offer_id: uuid.UUID, response_note: str | None = None) -> ShiftOffer | None:
        offer = await self.repo.get_by_id(offer_id)
        if not offer:
            return None
        if offer.status not in (OfferStatus.PROPOSED, OfferStatus.VIEWED):
            raise ValueError(f"Cannot reject offer in status {offer.status}")

        offer.status = OfferStatus.REJECTED
        offer.responded_at = utcnow_naive()
        offer.response_note = response_note
        await self.session.flush()
        return offer

    async def cancel(self, offer_id: uuid.UUID) -> ShiftOffer | None:
        offer = await self.repo.get_by_id(offer_id)
        if not offer:
            return None
        if offer.status not in (OfferStatus.PROPOSED, OfferStatus.VIEWED):
            raise ValueError(f"Cannot cancel offer in status {offer.status}")

        offer.status = OfferStatus.CANCELLED
        await self.session.flush()
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

        return len(expired)

    async def get_by_shift(self, shift_id: uuid.UUID) -> list[ShiftOffer]:
        return await self.repo.get_by_shift(shift_id)

    async def get_by_doctor(self, doctor_id: uuid.UUID) -> list[ShiftOffer]:
        return await self.repo.get_by_doctor(doctor_id)

    async def get_pending_by_doctor(self, doctor_id: uuid.UUID) -> list[ShiftOffer]:
        return await self.repo.get_pending_by_doctor(doctor_id)
