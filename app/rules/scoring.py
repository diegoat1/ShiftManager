import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import Institution, InstitutionSite
from app.models.reliability import DoctorReliabilityStats
from app.models.shift import Shift
from app.repositories.assignment import AssignmentRepository
from app.repositories.availability import AvailabilityRepository
from app.repositories.doctor import DoctorRepository
from app.repositories.shift import ShiftRepository
from app.utils.distance import haversine
from app.utils.enums import AvailabilityType


@dataclass
class ScoreBreakdown:
    availability: int = 0
    shift_preference: int = 0
    site_affinity: int = 0
    workload_balance: int = 0
    distance: int = 0
    extra_qualifications: int = 0
    reliability: int = 0
    fairness: int = 0
    cost_efficiency: int = 0

    @property
    def total(self) -> int:
        return (
            self.availability
            + self.shift_preference
            + self.site_affinity
            + self.workload_balance
            + self.distance
            + self.extra_qualifications
            + self.reliability
            + self.fairness
            + self.cost_efficiency
        )

    def to_dict(self) -> dict:
        return {
            "availability": self.availability,
            "shift_preference": self.shift_preference,
            "site_affinity": self.site_affinity,
            "workload_balance": self.workload_balance,
            "distance": self.distance,
            "extra_qualifications": self.extra_qualifications,
            "reliability": self.reliability,
            "fairness": self.fairness,
            "cost_efficiency": self.cost_efficiency,
        }


@dataclass
class ScoredDoctor:
    doctor_id: uuid.UUID
    score: int = 0
    breakdown: ScoreBreakdown = field(default_factory=ScoreBreakdown)
    distance_km: float | None = None
    certifications: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    years_experience: int = 0
    can_work_alone: bool = False
    can_emergency_vehicle: bool = False


class MatchScorer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.doctor_repo = DoctorRepository(session)
        self.shift_repo = ShiftRepository(session)
        self.assignment_repo = AssignmentRepository(session)
        self.availability_repo = AvailabilityRepository(session)

    async def score(self, doctor_id: uuid.UUID, shift: Shift) -> ScoredDoctor:
        doctor = await self.doctor_repo.get_with_relations(doctor_id)
        if not doctor:
            return ScoredDoctor(doctor_id=doctor_id)

        breakdown = ScoreBreakdown()

        # 1. Availability type (max 20)
        breakdown.availability = await self._score_availability(doctor_id, shift)

        # 2. Shift preference (max 10)
        breakdown.shift_preference = self._score_shift_preference(doctor, shift)

        # 3. Site affinity (max 15)
        breakdown.site_affinity = await self._score_site_affinity(doctor_id, shift)

        # 4. Workload balance (max 10)
        breakdown.workload_balance = await self._score_workload(doctor, shift)

        # 5. Distance (max 10)
        dist_score, dist_km = self._score_distance(doctor, shift)
        breakdown.distance = dist_score

        # 6. Extra qualifications (max 5)
        breakdown.extra_qualifications = self._score_extra_qualifications(doctor, shift)

        # 7. Reliability (max 15)
        breakdown.reliability = await self._score_reliability(doctor_id)

        # 8. Fairness (max 10)
        breakdown.fairness = await self._score_fairness(doctor, shift)

        # 9. Cost efficiency (max 5)
        breakdown.cost_efficiency = self._score_cost_efficiency(doctor, shift)

        # Build competency info
        certs = [
            c.certification_type.name
            for c in doctor.certifications
            if c.is_active and c.certification_type
        ]
        langs = [
            dl.language.name for dl in doctor.languages if dl.language
        ]

        return ScoredDoctor(
            doctor_id=doctor_id,
            score=breakdown.total,
            breakdown=breakdown,
            distance_km=dist_km,
            certifications=certs,
            languages=langs,
            years_experience=doctor.years_experience,
            can_work_alone=doctor.can_work_alone,
            can_emergency_vehicle=doctor.can_emergency_vehicle,
        )

    async def score_many(
        self, doctor_ids: list[uuid.UUID], shift: Shift
    ) -> list[ScoredDoctor]:
        results = []
        for did in doctor_ids:
            results.append(await self.score(did, shift))
        results.sort(key=lambda s: s.score, reverse=True)
        return results

    # --- Scoring dimensions ---

    async def _score_availability(self, doctor_id: uuid.UUID, shift: Shift) -> int:
        """Max 20 points."""
        avail = await self.availability_repo.get_availability_with_type(
            doctor_id, shift.date, shift.start_datetime.time(), shift.end_datetime.time()
        )
        if not avail:
            return 0
        if avail.availability_type == AvailabilityType.PREFERRED:
            return 20
        if avail.availability_type == AvailabilityType.AVAILABLE:
            return 12
        if avail.availability_type == AvailabilityType.RELUCTANT:
            return 4
        return 0

    def _score_shift_preference(self, doctor, shift: Shift) -> int:
        """Max 10 points."""
        prefs = doctor.preferences
        if not prefs:
            return 5

        is_night = shift.is_night
        is_weekend = shift.date.weekday() >= 5

        if is_night and prefs.prefers_night:
            return 10
        if not is_night and prefs.prefers_day:
            return 10
        if is_weekend and prefs.prefers_weekends:
            return 10
        if is_weekend and prefs.avoids_weekends:
            return 1
        return 5

    async def _score_site_affinity(self, doctor_id: uuid.UUID, shift: Shift) -> int:
        """Max 15 points."""
        now = datetime.utcnow()
        start_90d = now - timedelta(days=90)
        recent_shifts = await self.shift_repo.get_doctor_shifts(
            doctor_id, start=start_90d, end=now
        )

        if not recent_shifts:
            return 3

        target_site_id = shift.site_id
        recent_site_ids = {s.site_id for s in recent_shifts}

        if target_site_id in recent_site_ids:
            return 15

        target_site = shift.site
        if target_site:
            target_inst_id = target_site.institution_id
            result = await self.session.execute(
                select(InstitutionSite.institution_id).where(
                    InstitutionSite.id.in_(recent_site_ids)
                )
            )
            recent_inst_ids = {row[0] for row in result.all()}
            if target_inst_id in recent_inst_ids:
                return 10

            doctor = await self.doctor_repo.get_with_relations(doctor_id)
            if doctor and doctor.preferences and doctor.preferences.preferred_institution_types:
                pref_types = {
                    t.strip().lower()
                    for t in doctor.preferences.preferred_institution_types.split(",")
                    if t.strip()
                }
                inst = await self.session.get(Institution, target_inst_id)
                if inst and inst.institution_type:
                    if inst.institution_type.lower() in pref_types:
                        return 6

        return 3

    async def _score_workload(self, doctor, shift: Shift) -> int:
        """Max 10 points."""
        count = await self.assignment_repo.count_shifts_in_month(
            doctor.id, shift.date.year, shift.date.month
        )
        max_shifts = doctor.max_shifts_per_month or 20
        if max_shifts == 0:
            return 0
        ratio = count / max_shifts
        if ratio <= 0.25:
            return 10
        if ratio <= 0.50:
            return 8
        if ratio <= 0.75:
            return 5
        if ratio < 1.0:
            return 2
        return 0

    def _score_distance(self, doctor, shift: Shift) -> tuple[int, float | None]:
        """Max 10 points."""
        if doctor.lat is None or doctor.lon is None:
            return 5, None
        site = shift.site
        if not site or site.lat is None or site.lon is None:
            return 5, None
        dist = haversine(doctor.lat, doctor.lon, site.lat, site.lon)
        if dist <= 10:
            score = 10
        elif dist <= 25:
            score = 8
        elif dist <= 50:
            score = 5
        else:
            score = 2
        return score, round(dist, 1)

    def _score_extra_qualifications(self, doctor, shift: Shift) -> int:
        """Max 5 points."""
        points = 0

        required_cert_ids = {r.certification_type_id for r in shift.requirements if r.is_mandatory}
        doctor_cert_ids = {c.certification_type_id for c in doctor.certifications if c.is_active}
        extra_certs = len(doctor_cert_ids - required_cert_ids)
        points += min(extra_certs, 2)

        required_lang_ids = {r.language_id for r in shift.language_requirements}
        doctor_lang_ids = {dl.language_id for dl in doctor.languages}
        extra_langs = len(doctor_lang_ids - required_lang_ids)
        points += min(extra_langs, 1)

        if shift.min_years_experience > 0:
            extra_years = doctor.years_experience - shift.min_years_experience
            points += min(max(extra_years, 0), 2)
        else:
            points += min(doctor.years_experience, 2)

        return min(points, 5)

    async def _score_reliability(self, doctor_id: uuid.UUID) -> int:
        """Max 15 points. Based on historical offer response behavior."""
        stmt = select(DoctorReliabilityStats).where(
            DoctorReliabilityStats.doctor_id == doctor_id
        )
        result = await self.session.execute(stmt)
        stats = result.scalar_one_or_none()

        if not stats or stats.total_offers_received == 0:
            return 8  # Neutral for new doctors

        # Scale reliability_score (0-100) to 0-15
        return round(stats.reliability_score / 100 * 15)

    async def _score_fairness(self, doctor, shift: Shift) -> int:
        """Max 10 points. Favor doctors who have fewer recent assignments."""
        count = await self.assignment_repo.count_shifts_in_month(
            doctor.id, shift.date.year, shift.date.month
        )
        # Fewer assignments = higher score
        if count == 0:
            return 10
        if count <= 3:
            return 8
        if count <= 6:
            return 5
        if count <= 10:
            return 3
        return 1

    def _score_cost_efficiency(self, doctor, shift: Shift) -> int:
        """Max 5 points. Favor closer, less expensive doctors."""
        points = 0
        # Closer doctor = less travel cost
        if doctor.lat is not None and doctor.lon is not None:
            site = shift.site
            if site and site.lat is not None and site.lon is not None:
                dist = haversine(doctor.lat, doctor.lon, site.lat, site.lon)
                if dist <= 15:
                    points += 3
                elif dist <= 30:
                    points += 2
                else:
                    points += 1

        # No overnight stay needed = cost saving
        if not doctor.willing_overnight_stay:
            points += 1

        # Has own vehicle = no transport cost
        if doctor.has_own_vehicle:
            points += 1

        return min(points, 5)
