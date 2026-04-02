import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.doctor import Doctor
from app.models.requirement import CodeLevel
from app.models.shift import Shift
from app.repositories.assignment import AssignmentRepository
from app.repositories.availability import AvailabilityRepository
from app.repositories.doctor import DoctorRepository
from app.repositories.document import DocumentRepository, DocumentTypeRepository
from app.repositories.shift import ShiftRepository
from app.rules.constraints import MAX_CONSECUTIVE_DAYS, MAX_NIGHT_SHIFTS_PER_MONTH, MIN_REST_HOURS
from app.utils.distance import haversine
from app.utils.enums import AvailabilityType


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class AvailabilitySnapshot:
    """Captures why a doctor is or isn't available for a specific shift slot.

    - ``available=True``: a matching availability slot was found.
    - ``blocked_by_unavailability=True``: an approved absence period covers the shift date.
    - Both False at the same time means "no availability slot recorded".
    """

    available: bool
    blocked_by_unavailability: bool
    availability_type: AvailabilityType | None  # set only when available=True


@dataclass(slots=True)
class ShiftWindow:
    """Lightweight representation of an already-assigned shift used for overlap/rest checks."""

    shift_id: uuid.UUID
    date: date
    start_datetime: datetime
    end_datetime: datetime
    site_id: uuid.UUID | None


# ---------------------------------------------------------------------------
# Bulk context
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EligibilityContext:
    """All data needed to evaluate eligibility for a single shift across many doctors.

    Built once by ``EligibilityContextBuilder.build_for_shift()`` and consumed
    synchronously by ``EligibilityEngine.check_with_context()``.
    """

    shift: Shift
    doctors: dict[uuid.UUID, Doctor]
    availability_snapshot_by_doctor: dict[uuid.UUID, AvailabilitySnapshot]
    nearby_shifts_by_doctor: dict[uuid.UUID, list[ShiftWindow]]   # ±48 h window
    consecutive_days_by_doctor: dict[uuid.UUID, int]
    monthly_shift_count_by_doctor: dict[uuid.UUID, int]
    monthly_night_shift_count_by_doctor: dict[uuid.UUID, int]
    # doctor_id → {document_type_id → latest approved expiry (None = never expires)}
    approved_document_expiry_by_doctor: dict[uuid.UUID, dict[int, date | None]]
    mandatory_document_type_ids: set[int]
    code_level_order_by_id: dict[int, int]


# ---------------------------------------------------------------------------
# Eligibility engine
# ---------------------------------------------------------------------------

class EligibilityEngine:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def check(self, doctor_id: uuid.UUID, shift_id: uuid.UUID) -> tuple[bool, list[str], list[str]]:
        """Returns (is_eligible, failed_reasons, warnings).

        Builds a single-doctor context and delegates to ``check_with_context``.
        This ensures there is no logic duplication between the two paths.
        """
        ctx = await EligibilityContextBuilder(self.session).build_for_shift(
            shift_id, doctor_ids=[doctor_id]
        )
        return self.check_with_context(doctor_id, ctx)

    # ------------------------------------------------------------------
    # Pure synchronous evaluation — zero DB calls
    # ------------------------------------------------------------------

    def check_with_context(
        self,
        doctor_id: uuid.UUID,
        ctx: EligibilityContext,
    ) -> tuple[bool, list[str], list[str]]:
        """Evaluate eligibility using a pre-loaded context. No I/O."""
        doctor = ctx.doctors.get(doctor_id)
        if not doctor:
            return False, ["Doctor not found in context"], []

        shift = ctx.shift
        reasons: list[str] = []
        warnings: list[str] = []

        self._ctx_active_status(doctor, reasons)
        self._ctx_availability(doctor_id, ctx, reasons)
        self._ctx_certifications(doctor, shift, reasons)
        self._ctx_cert_expiry(doctor, shift, reasons)
        self._ctx_languages(doctor, shift, reasons, warnings)
        self._ctx_distance(doctor, shift, reasons, warnings)
        self._ctx_overlap(doctor_id, shift, ctx, reasons)
        self._ctx_rest_period(doctor_id, shift, ctx, reasons)
        self._ctx_consecutive_days(doctor_id, shift, ctx, reasons)
        self._ctx_night_shift_limit(doctor_id, shift, ctx, reasons)
        self._ctx_code_level(doctor, shift, ctx, reasons)
        self._ctx_independent_work(doctor, shift, reasons)
        self._ctx_emergency_vehicle(doctor, shift, reasons)
        self._ctx_years_experience(doctor, shift, reasons)
        self._ctx_monthly_shift_limit(doctor_id, doctor, shift, ctx, reasons)
        self._ctx_night_shift_limit_personal(doctor_id, doctor, shift, ctx, reasons)
        self._ctx_mandatory_documents(doctor_id, shift, ctx, reasons)
        self._ctx_document_expiry(doctor_id, shift, ctx, reasons)

        return len(reasons) == 0, reasons, warnings

    # ------------------------------------------------------------------
    # Private sync check helpers (prefix _ctx_ to avoid name collision)
    # ------------------------------------------------------------------

    def _ctx_active_status(self, doctor: Doctor, reasons: list[str]) -> None:
        if not doctor.is_active:
            reasons.append("Doctor is not active")

    def _ctx_availability(
        self,
        doctor_id: uuid.UUID,
        ctx: EligibilityContext,
        reasons: list[str],
    ) -> None:
        snap = ctx.availability_snapshot_by_doctor.get(doctor_id)
        if snap is None or not snap.available:
            reasons.append("Doctor is not available for this time slot")

    def _ctx_certifications(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        doctor_cert_ids = {c.certification_type_id for c in doctor.certifications if c.is_active}
        for req in shift.requirements:
            if req.is_mandatory and req.certification_type_id not in doctor_cert_ids:
                cert_name = req.certification_type.name if req.certification_type else str(req.certification_type_id)
                reasons.append(f"Missing mandatory certification: {cert_name}")

    def _ctx_cert_expiry(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        shift_date = shift.date
        required_ids = {r.certification_type_id for r in shift.requirements if r.is_mandatory}
        for cert in doctor.certifications:
            if cert.certification_type_id in required_ids and cert.expiry_date and cert.expiry_date < shift_date:
                cert_name = cert.certification_type.name if cert.certification_type else str(cert.certification_type_id)
                reasons.append(f"Certification expired: {cert_name} (expired {cert.expiry_date})")

    def _ctx_languages(
        self,
        doctor: Doctor,
        shift: Shift,
        reasons: list[str],
        warnings: list[str],
    ) -> None:
        doctor_langs = {dl.language_id: dl.proficiency_level for dl in doctor.languages}
        for req in shift.language_requirements:
            if req.language_id not in doctor_langs:
                lang_name = req.language.name if req.language else str(req.language_id)
                reasons.append(f"Missing required language: {lang_name}")
            elif doctor_langs[req.language_id] < req.min_proficiency:
                lang_name = req.language.name if req.language else str(req.language_id)
                warnings.append(
                    f"Language proficiency below required for {lang_name}: "
                    f"has {doctor_langs[req.language_id]}, needs {req.min_proficiency}"
                )

    def _ctx_distance(
        self,
        doctor: Doctor,
        shift: Shift,
        reasons: list[str],
        warnings: list[str],
    ) -> None:
        if doctor.lat is None or doctor.lon is None:
            return
        site = shift.site
        if not site or site.lat is None or site.lon is None:
            return
        dist = haversine(doctor.lat, doctor.lon, site.lat, site.lon)
        if dist > doctor.max_distance_km:
            if doctor.willing_to_relocate:
                warnings.append(
                    f"Distance {dist:.1f}km exceeds max {doctor.max_distance_km}km "
                    f"but doctor is willing to relocate"
                )
            else:
                reasons.append(f"Distance {dist:.1f}km exceeds doctor's max {doctor.max_distance_km}km")

    def _ctx_overlap(
        self,
        doctor_id: uuid.UUID,
        shift: Shift,
        ctx: EligibilityContext,
        reasons: list[str],
    ) -> None:
        for sw in ctx.nearby_shifts_by_doctor.get(doctor_id, []):
            if sw.shift_id == shift.id:
                continue
            if sw.start_datetime < shift.end_datetime and sw.end_datetime > shift.start_datetime:
                reasons.append(f"Overlaps with existing shift on {sw.date}")
                return

    def _ctx_rest_period(
        self,
        doctor_id: uuid.UUID,
        shift: Shift,
        ctx: EligibilityContext,
        reasons: list[str],
    ) -> None:
        for sw in ctx.nearby_shifts_by_doctor.get(doctor_id, []):
            if sw.shift_id == shift.id:
                continue
            if sw.end_datetime <= shift.start_datetime:
                gap = (shift.start_datetime - sw.end_datetime).total_seconds() / 3600
                if gap < MIN_REST_HOURS:
                    reasons.append(
                        f"Rest period {gap:.1f}h < required {MIN_REST_HOURS}h after shift on {sw.date}"
                    )
                    return
            elif sw.start_datetime >= shift.end_datetime:
                gap = (sw.start_datetime - shift.end_datetime).total_seconds() / 3600
                if gap < MIN_REST_HOURS:
                    reasons.append(
                        f"Rest period {gap:.1f}h < required {MIN_REST_HOURS}h before shift on {sw.date}"
                    )
                    return

    def _ctx_consecutive_days(
        self,
        doctor_id: uuid.UUID,
        shift: Shift,
        ctx: EligibilityContext,
        reasons: list[str],
    ) -> None:
        consecutive = ctx.consecutive_days_by_doctor.get(doctor_id, 1)
        if consecutive >= MAX_CONSECUTIVE_DAYS:
            reasons.append(
                f"Would exceed {MAX_CONSECUTIVE_DAYS} consecutive working days ({consecutive} already)"
            )

    def _ctx_night_shift_limit(
        self,
        doctor_id: uuid.UUID,
        shift: Shift,
        ctx: EligibilityContext,
        reasons: list[str],
    ) -> None:
        if not shift.is_night:
            return
        count = ctx.monthly_night_shift_count_by_doctor.get(doctor_id, 0)
        if count >= MAX_NIGHT_SHIFTS_PER_MONTH:
            reasons.append(
                f"Night shift limit reached: {count}/{MAX_NIGHT_SHIFTS_PER_MONTH} for "
                f"{shift.date.year}-{shift.date.month:02d}"
            )

    def _ctx_code_level(
        self,
        doctor: Doctor,
        shift: Shift,
        ctx: EligibilityContext,
        reasons: list[str],
    ) -> None:
        if shift.min_code_level_id is None or doctor.max_code_level_id is None:
            return
        doc_order = ctx.code_level_order_by_id.get(doctor.max_code_level_id)
        shift_order = ctx.code_level_order_by_id.get(shift.min_code_level_id)
        if doc_order is not None and shift_order is not None and doc_order < shift_order:
            reasons.append(
                f"Doctor's max code level (severity {doc_order}) "
                f"is below shift's required (severity {shift_order})"
            )

    def _ctx_independent_work(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        if shift.requires_independent_work and not doctor.can_work_alone:
            reasons.append("Shift requires independent work but doctor cannot work alone")

    def _ctx_emergency_vehicle(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        if shift.requires_emergency_vehicle and not doctor.can_emergency_vehicle:
            reasons.append("Shift requires emergency vehicle capability but doctor lacks it")

    def _ctx_years_experience(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        if shift.min_years_experience > 0 and doctor.years_experience < shift.min_years_experience:
            reasons.append(
                f"Doctor has {doctor.years_experience} years experience, "
                f"shift requires {shift.min_years_experience}"
            )

    def _ctx_monthly_shift_limit(
        self,
        doctor_id: uuid.UUID,
        doctor: Doctor,
        shift: Shift,
        ctx: EligibilityContext,
        reasons: list[str],
    ) -> None:
        if doctor.max_shifts_per_month >= 20:
            return
        count = ctx.monthly_shift_count_by_doctor.get(doctor_id, 0)
        if count >= doctor.max_shifts_per_month:
            reasons.append(
                f"Monthly shift limit reached: {count}/{doctor.max_shifts_per_month} for "
                f"{shift.date.year}-{shift.date.month:02d}"
            )

    def _ctx_night_shift_limit_personal(
        self,
        doctor_id: uuid.UUID,
        doctor: Doctor,
        shift: Shift,
        ctx: EligibilityContext,
        reasons: list[str],
    ) -> None:
        if not shift.is_night or doctor.max_night_shifts_per_month is None:
            return
        count = ctx.monthly_night_shift_count_by_doctor.get(doctor_id, 0)
        if count >= doctor.max_night_shifts_per_month:
            reasons.append(
                f"Personal night shift limit reached: {count}/{doctor.max_night_shifts_per_month} for "
                f"{shift.date.year}-{shift.date.month:02d}"
            )

    def _ctx_mandatory_documents(
        self,
        doctor_id: uuid.UUID,
        shift: Shift,
        ctx: EligibilityContext,
        reasons: list[str],
    ) -> None:
        if not ctx.mandatory_document_type_ids:
            return
        approved_types = set(ctx.approved_document_expiry_by_doctor.get(doctor_id, {}).keys())
        for type_id in ctx.mandatory_document_type_ids:
            if type_id not in approved_types:
                reasons.append(f"Missing mandatory document: type_id={type_id}")

    def _ctx_document_expiry(
        self,
        doctor_id: uuid.UUID,
        shift: Shift,
        ctx: EligibilityContext,
        reasons: list[str],
    ) -> None:
        shift_date = shift.date
        for type_id, expiry in ctx.approved_document_expiry_by_doctor.get(doctor_id, {}).items():
            if expiry is not None and expiry < shift_date:
                reasons.append(f"Document expired: type_id={type_id} (expired {expiry})")


# ---------------------------------------------------------------------------
# Pure-Python helpers
# ---------------------------------------------------------------------------

def _compute_consecutive(worked_dates: set[date], target_date: date) -> int:
    """Count consecutive working days around target_date (inclusive)."""
    count = 1
    d = target_date - timedelta(days=1)
    while d in worked_dates:
        count += 1
        d -= timedelta(days=1)
    d = target_date + timedelta(days=1)
    while d in worked_dates:
        count += 1
        d += timedelta(days=1)
    return count


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

class EligibilityContextBuilder:
    """Builds an ``EligibilityContext`` for a single shift in ≤12 SQL statements."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.shift_repo = ShiftRepository(session)
        self.doctor_repo = DoctorRepository(session)
        self.avail_repo = AvailabilityRepository(session)
        self.assignment_repo = AssignmentRepository(session)
        self.doc_repo = DocumentRepository(session)
        self.doc_type_repo = DocumentTypeRepository(session)

    async def build_for_shift(
        self,
        shift_id: uuid.UUID,
        doctor_ids: Iterable[uuid.UUID] | None = None,
        limit: int = 1000,
    ) -> EligibilityContext:
        # 1. Shift with requirements + site
        shift = await self.shift_repo.get_with_requirements(shift_id)
        if not shift:
            raise ValueError(f"Shift {shift_id} not found")

        # 2. Doctors with certifications/languages loaded in ≤4 queries
        ids = list(doctor_ids) if doctor_ids is not None else None
        doctors_list = await self.doctor_repo.get_all_with_relations(
            is_active=True if ids is None else None,
            doctor_ids=ids,
            limit=limit,
        )
        doctors = {d.id: d for d in doctors_list}
        all_ids = list(doctors.keys())

        if not all_ids:
            return EligibilityContext(
                shift=shift,
                doctors={},
                availability_snapshot_by_doctor={},
                nearby_shifts_by_doctor={},
                consecutive_days_by_doctor={},
                monthly_shift_count_by_doctor={},
                monthly_night_shift_count_by_doctor={},
                approved_document_expiry_by_doctor={},
                mandatory_document_type_ids=set(),
                code_level_order_by_id={},
            )

        shift_start_time = shift.start_datetime.time()
        shift_end_time = shift.end_datetime.time()

        # 3. Bulk availability (2 queries)
        avail_raw = await self.avail_repo.bulk_availability_for_shift(
            all_ids, shift.date, shift_start_time, shift_end_time
        )
        availability_snapshot_by_doctor = {
            did: AvailabilitySnapshot(
                available=tup[0],
                blocked_by_unavailability=tup[1],
                availability_type=tup[2],
            )
            for did, tup in avail_raw.items()
        }

        # 4. Nearby shifts for overlap/rest checks — ±48 h window (1 query)
        window_start = shift.start_datetime - timedelta(hours=48)
        window_end = shift.end_datetime + timedelta(hours=48)
        raw_nearby = await self.assignment_repo.bulk_nearby_shifts_data(all_ids, window_start, window_end)
        nearby_shifts_by_doctor: dict[uuid.UUID, list[ShiftWindow]] = {
            did: [
                ShiftWindow(shift_id=t[0], date=t[1], start_datetime=t[2], end_datetime=t[3], site_id=t[4])
                for t in rows
            ]
            for did, rows in raw_nearby.items()
        }

        # 5. Consecutive days (1 query + pure Python)
        consecutive_days_by_doctor = await self.assignment_repo.bulk_consecutive_days(all_ids, shift.date)

        # 6. Monthly counts (2 queries)
        monthly_shift_count_by_doctor = await self.assignment_repo.bulk_shifts_in_month(
            all_ids, shift.date.year, shift.date.month
        )
        monthly_night_shift_count_by_doctor = await self.assignment_repo.bulk_night_shifts_in_month(
            all_ids, shift.date.year, shift.date.month
        )

        # 7. Document info (1 query + 1 query for mandatory types)
        approved_document_expiry_by_doctor = await self.doc_repo.bulk_approved_expiry_by_doctors(all_ids)
        mandatory_types = await self.doc_type_repo.get_mandatory()
        mandatory_document_type_ids = {dt.id for dt in mandatory_types}

        # 8. Code level severities (1 query)
        cl_result = await self.session.execute(select(CodeLevel.id, CodeLevel.severity_order))
        code_level_order_by_id = {row[0]: row[1] for row in cl_result.all()}

        return EligibilityContext(
            shift=shift,
            doctors=doctors,
            availability_snapshot_by_doctor=availability_snapshot_by_doctor,
            nearby_shifts_by_doctor=nearby_shifts_by_doctor,
            consecutive_days_by_doctor=consecutive_days_by_doctor,
            monthly_shift_count_by_doctor=monthly_shift_count_by_doctor,
            monthly_night_shift_count_by_doctor=monthly_night_shift_count_by_doctor,
            approved_document_expiry_by_doctor=approved_document_expiry_by_doctor,
            mandatory_document_type_ids=mandatory_document_type_ids,
            code_level_order_by_id=code_level_order_by_id,
        )


class DoctorShiftsContextBuilder:
    """Builds one EligibilityContext per shift for a single doctor across N shifts.

    Fires ≤ 9 + 2M queries regardless of N (M = distinct year-months in shifts).
    Shifts must be pre-loaded with requirements and site (selectinload already done
    upstream in get_available_shifts_for_doctor).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.doctor_repo = DoctorRepository(session)
        self.avail_repo = AvailabilityRepository(session)
        self.assignment_repo = AssignmentRepository(session)
        self.doc_repo = DocumentRepository(session)
        self.doc_type_repo = DocumentTypeRepository(session)

    async def build(
        self,
        doctor_id: uuid.UUID,
        shifts: list,  # list[Shift] — already loaded with requirements + site
    ) -> dict[uuid.UUID, EligibilityContext]:
        """Return dict[shift_id → EligibilityContext]. Raises ValueError if doctor not found."""
        if not shifts:
            return {}

        # Q1 — doctor with certifications / languages / preferences
        doctors_list = await self.doctor_repo.get_all_with_relations(
            is_active=None, doctor_ids=[doctor_id], limit=1
        )
        if not doctors_list:
            raise ValueError(f"Doctor {doctor_id} not found")
        doctors = {d.id: d for d in doctors_list}

        # Q2–Q3 — availability snapshot per shift (2 queries)
        snap_by_shift_id: dict[uuid.UUID, AvailabilitySnapshot] = (
            await self.avail_repo.bulk_availability_for_doctor_and_shifts(doctor_id, shifts)
        )

        # Shared date bounds
        min_date = min(s.date for s in shifts)
        max_date = max(s.date for s in shifts)

        # Q4 — assignments in ±48h window (for overlap / rest checks)
        window_start = datetime(min_date.year, min_date.month, min_date.day) - timedelta(hours=48)
        window_end = datetime(max_date.year, max_date.month, max_date.day, 23, 59, 59) + timedelta(hours=48)
        raw_nearby = await self.assignment_repo.bulk_nearby_shifts_data(
            [doctor_id], window_start, window_end
        )
        all_windows: list[ShiftWindow] = [
            ShiftWindow(shift_id=t[0], date=t[1], start_datetime=t[2], end_datetime=t[3], site_id=t[4])
            for t in raw_nearby.get(doctor_id, [])
        ]

        # Q5 — worked dates for consecutive-days computation (±14 days, PROPOSED|CONFIRMED)
        consec_start = min_date - timedelta(days=14)
        consec_end = max_date + timedelta(days=14)
        worked_dates = await self.assignment_repo.get_worked_dates_for_doctor(
            doctor_id, consec_start, consec_end
        )

        # Q6×M + Q7×M — monthly shift + night counts (2 queries per distinct month)
        unique_months: set[tuple[int, int]] = {(s.date.year, s.date.month) for s in shifts}
        monthly_counts: dict[tuple[int, int], int] = {}
        monthly_night_counts: dict[tuple[int, int], int] = {}
        for year, month in unique_months:
            counts = await self.assignment_repo.bulk_shifts_in_month([doctor_id], year, month)
            monthly_counts[(year, month)] = counts.get(doctor_id, 0)
            night_counts = await self.assignment_repo.bulk_night_shifts_in_month([doctor_id], year, month)
            monthly_night_counts[(year, month)] = night_counts.get(doctor_id, 0)

        # Q8 — code level severities
        cl_result = await self.session.execute(select(CodeLevel.id, CodeLevel.severity_order))
        code_level_order_by_id = {row[0]: row[1] for row in cl_result.all()}

        # Q9 — mandatory document types
        mandatory_types = await self.doc_type_repo.get_mandatory()
        mandatory_document_type_ids = {dt.id for dt in mandatory_types}

        # Q10 — doctor's approved document expiry
        approved_document_expiry_by_doctor = await self.doc_repo.bulk_approved_expiry_by_doctors(
            [doctor_id]
        )

        # Build one EligibilityContext per shift (pure Python)
        out: dict[uuid.UUID, EligibilityContext] = {}
        for shift in shifts:
            shift_start = shift.start_datetime
            shift_end = shift.end_datetime

            nearby_for_shift = [
                w for w in all_windows
                if w.shift_id != shift.id
                and w.start_datetime < shift_end + timedelta(hours=48)
                and w.end_datetime > shift_start - timedelta(hours=48)
            ]

            out[shift.id] = EligibilityContext(
                shift=shift,
                doctors=doctors,
                availability_snapshot_by_doctor={
                    doctor_id: snap_by_shift_id.get(
                        shift.id,
                        AvailabilitySnapshot(available=False, blocked_by_unavailability=False, availability_type=None),
                    )
                },
                nearby_shifts_by_doctor={doctor_id: nearby_for_shift},
                consecutive_days_by_doctor={
                    doctor_id: _compute_consecutive(worked_dates, shift.date)
                },
                monthly_shift_count_by_doctor={
                    doctor_id: monthly_counts.get((shift.date.year, shift.date.month), 0)
                },
                monthly_night_shift_count_by_doctor={
                    doctor_id: monthly_night_counts.get((shift.date.year, shift.date.month), 0)
                },
                approved_document_expiry_by_doctor=approved_document_expiry_by_doctor,
                mandatory_document_type_ids=mandatory_document_type_ids,
                code_level_order_by_id=code_level_order_by_id,
            )

        return out
