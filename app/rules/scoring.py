import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.doctor import Doctor
from app.models.institution import Institution, InstitutionSite
from app.models.reliability import DoctorReliabilityStats
from app.models.shift import Shift
from app.repositories.assignment import AssignmentRepository
from app.repositories.availability import AvailabilityRepository
from app.repositories.doctor import DoctorRepository
from app.repositories.reliability import ReliabilityRepository
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


# ---------------------------------------------------------------------------
# Scoring context (1 doctor × N shifts)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DoctorShiftsScoringContext:
    """Pre-loaded data for scoring one doctor across many shifts.

    Built by ``DoctorShiftsScoringContextBuilder.build()`` and consumed
    synchronously by ``MatchScorer.score_with_context()``.
    """

    doctor: Doctor  # with certifications, languages, preferences
    availability_type_by_shift_id: dict[uuid.UUID, AvailabilityType | None]
    monthly_shift_count_by_month: dict[tuple[int, int], int]  # (year, month) → count
    recent_site_ids_90d: set[uuid.UUID]
    recent_institution_ids_90d: set[uuid.UUID]
    reliability_score: float | None


class DoctorShiftsScoringContextBuilder:
    """Builds a DoctorShiftsScoringContext for one doctor across N shifts.

    When called after the eligibility builder, fires only 3 NEW queries
    (availability types, site affinity, reliability). Monthly counts are
    reused from the eligibility context via the optional parameter.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.avail_repo = AvailabilityRepository(session)
        self.shift_repo = ShiftRepository(session)
        self.assignment_repo = AssignmentRepository(session)

    async def build(
        self,
        doctor: Doctor,
        shifts: list,  # list[Shift]
        monthly_shift_count_by_month: dict[tuple[int, int], int] | None = None,
    ) -> DoctorShiftsScoringContext:
        if not shifts:
            return DoctorShiftsScoringContext(
                doctor=doctor,
                availability_type_by_shift_id={},
                monthly_shift_count_by_month=monthly_shift_count_by_month or {},
                recent_site_ids_90d=set(),
                recent_institution_ids_90d=set(),
                reliability_score=None,
            )

        # Q1 — raw availability type per shift (1 query, no unavailability check)
        availability_type_by_shift_id = (
            await self.avail_repo.bulk_availability_type_for_doctor_and_shifts(doctor.id, shifts)
        )

        # Q2 — site affinity: recent site_ids + institution_ids (1 query)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        since_90d = now - timedelta(days=90)
        recent_site_ids, recent_inst_ids = (
            await self.shift_repo.get_recent_site_affinity_for_doctor(doctor.id, since_90d)
        )

        # Q3 — reliability score (1 query)
        rel_result = await self.session.execute(
            select(DoctorReliabilityStats.reliability_score).where(
                DoctorReliabilityStats.doctor_id == doctor.id
            )
        )
        reliability_score = rel_result.scalar_one_or_none()

        # Monthly counts — reuse from eligibility context or load fresh
        if monthly_shift_count_by_month is None:
            unique_months = {(s.date.year, s.date.month) for s in shifts}
            monthly_shift_count_by_month = {}
            for year, month in unique_months:
                counts = await self.assignment_repo.bulk_shifts_in_month([doctor.id], year, month)
                monthly_shift_count_by_month[(year, month)] = counts.get(doctor.id, 0)

        return DoctorShiftsScoringContext(
            doctor=doctor,
            availability_type_by_shift_id=availability_type_by_shift_id,
            monthly_shift_count_by_month=monthly_shift_count_by_month,
            recent_site_ids_90d=recent_site_ids,
            recent_institution_ids_90d=recent_inst_ids,
            reliability_score=reliability_score,
        )


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------

class MatchScorer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.doctor_repo = DoctorRepository(session)
        self.shift_repo = ShiftRepository(session)
        self.assignment_repo = AssignmentRepository(session)
        self.availability_repo = AvailabilityRepository(session)

    async def score(self, doctor_id: uuid.UUID, shift: Shift) -> ScoredDoctor:
        """Compatibility wrapper — builds a single-shift context and delegates."""
        doctor = await self.doctor_repo.get_with_relations(doctor_id)
        if not doctor:
            return ScoredDoctor(doctor_id=doctor_id)

        ctx = await DoctorShiftsScoringContextBuilder(self.session).build(
            doctor=doctor, shifts=[shift],
        )
        return self.score_with_context(shift, ctx)

    def score_with_context(
        self, shift: Shift, ctx: DoctorShiftsScoringContext
    ) -> ScoredDoctor:
        """Synchronous scoring — zero DB calls."""
        doctor = ctx.doctor
        breakdown = ScoreBreakdown()

        # 1. Availability type (max 20)
        breakdown.availability = self._ctx_score_availability(shift, ctx)

        # 2. Shift preference (max 10)
        breakdown.shift_preference = self._ctx_score_shift_preference(doctor, shift)

        # 3. Site affinity (max 15)
        breakdown.site_affinity = self._ctx_score_site_affinity(shift, ctx)

        # 4. Workload balance (max 10)
        breakdown.workload_balance = self._ctx_score_workload(doctor, shift, ctx)

        # 5. Distance (max 10)
        dist_score, dist_km = self._ctx_score_distance(doctor, shift)
        breakdown.distance = dist_score

        # 6. Extra qualifications (max 5)
        breakdown.extra_qualifications = self._ctx_score_extra_qualifications(doctor, shift)

        # 7. Reliability (max 15)
        breakdown.reliability = self._ctx_score_reliability(ctx)

        # 8. Fairness (max 10)
        breakdown.fairness = self._ctx_score_fairness(doctor, shift, ctx)

        # 9. Cost efficiency (max 5)
        breakdown.cost_efficiency = self._ctx_score_cost_efficiency(doctor, shift)

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
            doctor_id=doctor.id,
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
        """Compatibility wrapper — scores each doctor individually."""
        results = []
        for did in doctor_ids:
            results.append(await self.score(did, shift))
        results.sort(key=lambda s: s.score, reverse=True)
        return results

    async def score_many_with_eligibility_context(
        self,
        doctor_ids: list[uuid.UUID],
        shift: Shift,
        eligibility_ctx: "EligibilityContext",
    ) -> list[ScoredDoctor]:
        """Score N doctors for 1 shift, reusing data from EligibilityContext.

        Fires only 2 NEW queries (bulk site affinity + bulk reliability).
        Availability types are extracted from the eligibility snapshot — safe because
        only eligible doctors (not blocked by unavailability) reach this path.
        """
        from app.rules.eligibility import EligibilityContext  # type hint only

        if not doctor_ids:
            return []

        # Q1 — bulk site affinity for all doctors (1 query)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        since_90d = now - timedelta(days=90)
        site_affinity = await self.shift_repo.bulk_get_recent_site_affinity_for_doctors(
            doctor_ids, since_90d
        )

        # Q2 — bulk reliability scores (1 query)
        reliability_repo = ReliabilityRepository(self.session)
        reliability = await reliability_repo.bulk_get_reliability_scores(doctor_ids)

        # Build per-doctor scoring context from pre-loaded data (pure Python)
        results: list[ScoredDoctor] = []
        for did in doctor_ids:
            doctor = eligibility_ctx.doctors.get(did)
            if not doctor:
                results.append(ScoredDoctor(doctor_id=did))
                continue

            snap = eligibility_ctx.availability_snapshot_by_doctor.get(did)
            avail_type = snap.availability_type if snap else None

            site_ids, inst_ids = site_affinity.get(did, (set(), set()))

            ctx = DoctorShiftsScoringContext(
                doctor=doctor,
                availability_type_by_shift_id={shift.id: avail_type},
                monthly_shift_count_by_month={
                    (shift.date.year, shift.date.month): (
                        eligibility_ctx.monthly_shift_count_by_doctor.get(did, 0)
                    )
                },
                recent_site_ids_90d=site_ids,
                recent_institution_ids_90d=inst_ids,
                reliability_score=reliability.get(did),
            )
            results.append(self.score_with_context(shift, ctx))

        results.sort(key=lambda s: s.score, reverse=True)
        return results

    # --- Sync scoring dimensions (ctx_ prefix) ---

    def _ctx_score_availability(self, shift: Shift, ctx: DoctorShiftsScoringContext) -> int:
        """Max 20 points. Uses raw availability type (no unavailability filter)."""
        avail_type = ctx.availability_type_by_shift_id.get(shift.id)
        if avail_type is None:
            return 0
        if avail_type == AvailabilityType.PREFERRED:
            return 20
        if avail_type == AvailabilityType.AVAILABLE:
            return 12
        if avail_type == AvailabilityType.RELUCTANT:
            return 4
        return 0

    def _ctx_score_shift_preference(self, doctor: Doctor, shift: Shift) -> int:
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

    def _ctx_score_site_affinity(self, shift: Shift, ctx: DoctorShiftsScoringContext) -> int:
        """Max 15 points."""
        if not ctx.recent_site_ids_90d:
            return 3

        if shift.site_id in ctx.recent_site_ids_90d:
            return 15

        target_site = shift.site
        if target_site and target_site.institution_id in ctx.recent_institution_ids_90d:
            return 10

        # institution_type branch removed — field does not exist on Institution model
        return 3

    def _ctx_score_workload(
        self, doctor: Doctor, shift: Shift, ctx: DoctorShiftsScoringContext
    ) -> int:
        """Max 10 points."""
        count = ctx.monthly_shift_count_by_month.get(
            (shift.date.year, shift.date.month), 0
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

    def _ctx_score_distance(self, doctor: Doctor, shift: Shift) -> tuple[int, float | None]:
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

    def _ctx_score_extra_qualifications(self, doctor: Doctor, shift: Shift) -> int:
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

    def _ctx_score_reliability(self, ctx: DoctorShiftsScoringContext) -> int:
        """Max 15 points. Based on historical offer response behavior."""
        if ctx.reliability_score is None:
            return 8  # Neutral for new doctors
        return round(ctx.reliability_score / 100 * 15)

    def _ctx_score_fairness(
        self, doctor: Doctor, shift: Shift, ctx: DoctorShiftsScoringContext
    ) -> int:
        """Max 10 points. Favor doctors who have fewer recent assignments."""
        count = ctx.monthly_shift_count_by_month.get(
            (shift.date.year, shift.date.month), 0
        )
        if count == 0:
            return 10
        if count <= 3:
            return 8
        if count <= 6:
            return 5
        if count <= 10:
            return 3
        return 1

    def _ctx_score_cost_efficiency(self, doctor: Doctor, shift: Shift) -> int:
        """Max 5 points. Favor closer, less expensive doctors."""
        points = 0
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

        if not doctor.willing_overnight_stay:
            points += 1

        if doctor.has_own_vehicle:
            points += 1

        return min(points, 5)
