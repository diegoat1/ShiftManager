import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import Institution, InstitutionSite
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

    @property
    def total(self) -> int:
        return (
            self.availability
            + self.shift_preference
            + self.site_affinity
            + self.workload_balance
            + self.distance
            + self.extra_qualifications
        )

    def to_dict(self) -> dict:
        return {
            "availability": self.availability,
            "shift_preference": self.shift_preference,
            "site_affinity": self.site_affinity,
            "workload_balance": self.workload_balance,
            "distance": self.distance,
            "extra_qualifications": self.extra_qualifications,
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

        # 1. Availability type (max 25)
        breakdown.availability = await self._score_availability(doctor_id, shift)

        # 2. Shift preference (max 15)
        breakdown.shift_preference = self._score_shift_preference(doctor, shift)

        # 3. Site affinity (max 20)
        breakdown.site_affinity = await self._score_site_affinity(doctor_id, shift)

        # 4. Workload balance (max 15)
        breakdown.workload_balance = await self._score_workload(doctor, shift)

        # 5. Distance (max 15)
        dist_score, dist_km = self._score_distance(doctor, shift)
        breakdown.distance = dist_score

        # 6. Extra qualifications (max 10)
        breakdown.extra_qualifications = self._score_extra_qualifications(doctor, shift)

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
        avail = await self.availability_repo.get_availability_with_type(
            doctor_id, shift.date, shift.start_datetime.time(), shift.end_datetime.time()
        )
        if not avail:
            return 0
        if avail.availability_type == AvailabilityType.PREFERRED:
            return 25
        if avail.availability_type == AvailabilityType.AVAILABLE:
            return 15
        if avail.availability_type == AvailabilityType.RELUCTANT:
            return 5
        return 0

    def _score_shift_preference(self, doctor, shift: Shift) -> int:
        prefs = doctor.preferences
        if not prefs:
            return 8  # neutral

        is_night = shift.is_night
        is_weekend = shift.date.weekday() >= 5

        if is_night and prefs.prefers_night:
            return 15
        if not is_night and prefs.prefers_day:
            return 15
        if is_weekend and prefs.prefers_weekends:
            return 15
        if is_weekend and prefs.avoids_weekends:
            return 2
        return 8

    async def _score_site_affinity(self, doctor_id: uuid.UUID, shift: Shift) -> int:
        now = datetime.utcnow()
        start_90d = now - timedelta(days=90)
        recent_shifts = await self.shift_repo.get_doctor_shifts(
            doctor_id, start=start_90d, end=now
        )

        if not recent_shifts:
            return 4

        target_site_id = shift.site_id
        recent_site_ids = {s.site_id for s in recent_shifts}

        # Same site
        if target_site_id in recent_site_ids:
            return 20

        # Same institution — load institution_id for target site and recent sites
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
                return 12

            # Preferred institution types
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
                        return 8

        return 4

    async def _score_workload(self, doctor, shift: Shift) -> int:
        count = await self.assignment_repo.count_shifts_in_month(
            doctor.id, shift.date.year, shift.date.month
        )
        max_shifts = doctor.max_shifts_per_month or 20
        if max_shifts == 0:
            return 0
        ratio = count / max_shifts
        if ratio <= 0.25:
            return 15
        if ratio <= 0.50:
            return 12
        if ratio <= 0.75:
            return 8
        if ratio < 1.0:
            return 4
        return 0

    def _score_distance(self, doctor, shift: Shift) -> tuple[int, float | None]:
        if doctor.lat is None or doctor.lon is None:
            return 8, None
        site = shift.site
        if not site or site.lat is None or site.lon is None:
            return 8, None
        dist = haversine(doctor.lat, doctor.lon, site.lat, site.lon)
        if dist <= 10:
            score = 15
        elif dist <= 25:
            score = 12
        elif dist <= 50:
            score = 8
        else:
            score = 3
        return score, round(dist, 1)

    def _score_extra_qualifications(self, doctor, shift: Shift) -> int:
        points = 0

        # Extra certs beyond required
        required_cert_ids = {r.certification_type_id for r in shift.requirements if r.is_mandatory}
        doctor_cert_ids = {c.certification_type_id for c in doctor.certifications if c.is_active}
        extra_certs = len(doctor_cert_ids - required_cert_ids)
        points += min(extra_certs, 4)

        # Extra languages beyond required
        required_lang_ids = {r.language_id for r in shift.language_requirements}
        doctor_lang_ids = {dl.language_id for dl in doctor.languages}
        extra_langs = len(doctor_lang_ids - required_lang_ids)
        points += min(extra_langs, 2)

        # Experience above minimum
        if shift.min_years_experience > 0:
            extra_years = doctor.years_experience - shift.min_years_experience
            points += min(max(extra_years, 0), 4)
        else:
            points += min(doctor.years_experience, 4)

        return min(points, 10)
