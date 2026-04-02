import uuid
from app.utils.dates import utcnow_naive

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.offer import ShiftOffer
from app.models.reliability import DoctorReliabilityStats
from app.models.doctor import Doctor
from app.repositories.reliability import ReliabilityRepository
from app.utils.enums import OfferStatus


class ReliabilityService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ReliabilityRepository(session)

    async def calculate_for_doctor(self, doctor_id: uuid.UUID) -> DoctorReliabilityStats:
        # Count offers by status
        stmt = select(ShiftOffer).where(ShiftOffer.doctor_id == doctor_id)
        result = await self.session.execute(stmt)
        offers = list(result.scalars().all())

        total = len(offers)
        accepted = sum(1 for o in offers if o.status == OfferStatus.ACCEPTED)
        rejected = sum(1 for o in offers if o.status == OfferStatus.REJECTED)
        expired = sum(1 for o in offers if o.status == OfferStatus.EXPIRED)
        cancelled = sum(1 for o in offers if o.status == OfferStatus.CANCELLED)

        # Avg response time
        responded = [o for o in offers if o.responded_at and o.offered_at]
        avg_response = 0.0
        if responded:
            total_minutes = sum(
                (o.responded_at - o.offered_at).total_seconds() / 60 for o in responded
            )
            avg_response = total_minutes / len(responded)

        acceptance_rate = (accepted / total * 100) if total > 0 else 0.0

        # Reliability score: 0-100
        # Base 50, +30 for acceptance rate, -20 for expired/cancelled, +20 for response speed
        score = 50.0
        if total > 0:
            score += (acceptance_rate / 100) * 30
            expire_penalty = min((expired + cancelled) / max(total, 1) * 20, 20)
            score -= expire_penalty
            # Fast response bonus (< 60 min avg = full bonus)
            if avg_response > 0 and avg_response < 60:
                score += 20
            elif avg_response > 0 and avg_response < 180:
                score += 10
            elif avg_response > 0:
                score += 5
        score = max(0.0, min(100.0, score))

        # Upsert
        stats = await self.repo.get_by_doctor(doctor_id)
        if stats:
            stats.total_offers_received = total
            stats.total_offers_accepted = accepted
            stats.total_offers_rejected = rejected
            stats.total_offers_expired = expired
            stats.total_cancellations = cancelled
            stats.avg_response_time_minutes = round(avg_response, 1)
            stats.acceptance_rate = round(acceptance_rate, 1)
            stats.reliability_score = round(score, 1)
            stats.last_calculated_at = utcnow_naive()
            await self.session.flush()
        else:
            stats = DoctorReliabilityStats(
                doctor_id=doctor_id,
                total_offers_received=total,
                total_offers_accepted=accepted,
                total_offers_rejected=rejected,
                total_offers_expired=expired,
                total_cancellations=cancelled,
                avg_response_time_minutes=round(avg_response, 1),
                acceptance_rate=round(acceptance_rate, 1),
                reliability_score=round(score, 1),
                last_calculated_at=utcnow_naive(),
            )
            self.session.add(stats)
            await self.session.flush()


        return stats

    async def recalculate_all(self) -> int:
        stmt = select(Doctor.id).where(Doctor.is_active == True)
        result = await self.session.execute(stmt)
        doctor_ids = [row[0] for row in result.all()]

        for doctor_id in doctor_ids:
            await self.calculate_for_doctor(doctor_id)

        return len(doctor_ids)

    async def get_stats(self, doctor_id: uuid.UUID) -> DoctorReliabilityStats | None:
        return await self.repo.get_by_doctor(doctor_id)

    async def get_all_stats(self, skip: int = 0, limit: int = 50):
        return await self.repo.get_all_stats(skip, limit)
