import uuid
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.doctor import Doctor
from app.models.requirement import CodeLevel
from app.models.shift import Shift
from app.repositories.assignment import AssignmentRepository
from app.repositories.availability import AvailabilityRepository
from app.repositories.doctor import DoctorRepository
from app.repositories.shift import ShiftRepository
from app.rules.constraints import MAX_CONSECUTIVE_DAYS, MAX_NIGHT_SHIFTS_PER_MONTH, MIN_REST_HOURS
from app.utils.distance import haversine


class EligibilityEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.doctor_repo = DoctorRepository(session)
        self.shift_repo = ShiftRepository(session)
        self.assignment_repo = AssignmentRepository(session)
        self.availability_repo = AvailabilityRepository(session)

    async def check(self, doctor_id: uuid.UUID, shift_id: uuid.UUID) -> tuple[bool, list[str], list[str]]:
        """Returns (is_eligible, failed_reasons, warnings)."""
        doctor = await self.doctor_repo.get_with_relations(doctor_id)
        shift = await self.shift_repo.get_with_requirements(shift_id)

        if not doctor or not shift:
            return False, ["Doctor or shift not found"], []

        reasons: list[str] = []
        warnings: list[str] = []

        await self._check_active_status(doctor, reasons)
        await self._check_availability(doctor, shift, reasons)
        await self._check_certifications(doctor, shift, reasons)
        await self._check_cert_expiry(doctor, shift, reasons)
        await self._check_languages(doctor, shift, reasons, warnings)
        await self._check_distance(doctor, shift, reasons, warnings)
        await self._check_overlap(doctor, shift, reasons)
        await self._check_rest_period(doctor, shift, reasons)
        await self._check_consecutive_days(doctor, shift, reasons)
        await self._check_night_shift_limit(doctor, shift, reasons)
        # Extended checks
        await self._check_code_level(doctor, shift, reasons)
        await self._check_independent_work(doctor, shift, reasons)
        await self._check_emergency_vehicle(doctor, shift, reasons)
        await self._check_years_experience(doctor, shift, reasons)
        await self._check_monthly_shift_limit(doctor, shift, reasons)
        await self._check_night_shift_limit_personal(doctor, shift, reasons)

        return len(reasons) == 0, reasons, warnings

    async def _check_active_status(self, doctor: Doctor, reasons: list[str]) -> None:
        if not doctor.is_active:
            reasons.append("Doctor is not active")

    async def _check_availability(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        start_time = shift.start_datetime.time()
        end_time = shift.end_datetime.time()
        is_avail = await self.availability_repo.is_available(
            doctor.id, shift.date, start_time, end_time
        )
        if not is_avail:
            reasons.append("Doctor is not available for this time slot")

    async def _check_certifications(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        doctor_cert_ids = {c.certification_type_id for c in doctor.certifications if c.is_active}
        for req in shift.requirements:
            if req.is_mandatory and req.certification_type_id not in doctor_cert_ids:
                cert_name = req.certification_type.name if req.certification_type else str(req.certification_type_id)
                reasons.append(f"Missing mandatory certification: {cert_name}")

    async def _check_cert_expiry(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        shift_date = shift.date
        for cert in doctor.certifications:
            if cert.expiry_date and cert.expiry_date < shift_date:
                # Check if this cert is required by the shift
                required_ids = {r.certification_type_id for r in shift.requirements if r.is_mandatory}
                if cert.certification_type_id in required_ids:
                    cert_name = cert.certification_type.name if cert.certification_type else str(cert.certification_type_id)
                    reasons.append(f"Certification expired: {cert_name} (expired {cert.expiry_date})")

    async def _check_languages(self, doctor: Doctor, shift: Shift, reasons: list[str], warnings: list[str]) -> None:
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

    async def _check_distance(self, doctor: Doctor, shift: Shift, reasons: list[str], warnings: list[str]) -> None:
        if doctor.lat is None or doctor.lon is None:
            return  # Can't check distance without coordinates
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

    async def _check_overlap(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        doctor_shifts = await self.shift_repo.get_doctor_shifts(
            doctor.id,
            start=shift.start_datetime - timedelta(hours=24),
            end=shift.end_datetime + timedelta(hours=24),
        )
        for existing in doctor_shifts:
            if existing.id == shift.id:
                continue
            if existing.start_datetime < shift.end_datetime and existing.end_datetime > shift.start_datetime:
                reasons.append(f"Overlaps with existing shift on {existing.date}")
                return

    async def _check_rest_period(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        doctor_shifts = await self.shift_repo.get_doctor_shifts(
            doctor.id,
            start=shift.start_datetime - timedelta(hours=48),
            end=shift.end_datetime + timedelta(hours=48),
        )
        for existing in doctor_shifts:
            if existing.id == shift.id:
                continue
            # Gap between shifts
            if existing.end_datetime <= shift.start_datetime:
                gap = (shift.start_datetime - existing.end_datetime).total_seconds() / 3600
                if gap < MIN_REST_HOURS:
                    reasons.append(f"Rest period {gap:.1f}h < required {MIN_REST_HOURS}h after shift on {existing.date}")
                    return
            elif existing.start_datetime >= shift.end_datetime:
                gap = (existing.start_datetime - shift.end_datetime).total_seconds() / 3600
                if gap < MIN_REST_HOURS:
                    reasons.append(f"Rest period {gap:.1f}h < required {MIN_REST_HOURS}h before shift on {existing.date}")
                    return

    async def _check_consecutive_days(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        consecutive = await self.assignment_repo.count_consecutive_days(doctor.id, shift.date)
        if consecutive >= MAX_CONSECUTIVE_DAYS:
            reasons.append(f"Would exceed {MAX_CONSECUTIVE_DAYS} consecutive working days ({consecutive} already)")

    async def _check_night_shift_limit(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        if not shift.is_night:
            return
        count = await self.assignment_repo.count_night_shifts_in_month(
            doctor.id, shift.date.year, shift.date.month
        )
        if count >= MAX_NIGHT_SHIFTS_PER_MONTH:
            reasons.append(
                f"Night shift limit reached: {count}/{MAX_NIGHT_SHIFTS_PER_MONTH} for "
                f"{shift.date.year}-{shift.date.month:02d}"
            )

    # --- Extended checks for Italian medical context ---

    async def _check_code_level(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        if shift.min_code_level_id is None or doctor.max_code_level_id is None:
            return
        # Load severity orders
        doctor_level = await self.session.get(CodeLevel, doctor.max_code_level_id)
        shift_level = await self.session.get(CodeLevel, shift.min_code_level_id)
        if not doctor_level or not shift_level:
            return
        if doctor_level.severity_order < shift_level.severity_order:
            reasons.append(
                f"Doctor's max code level ({doctor_level.code}, severity {doctor_level.severity_order}) "
                f"is below shift's required ({shift_level.code}, severity {shift_level.severity_order})"
            )

    async def _check_independent_work(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        if shift.requires_independent_work and not doctor.can_work_alone:
            reasons.append("Shift requires independent work but doctor cannot work alone")

    async def _check_emergency_vehicle(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        if shift.requires_emergency_vehicle and not doctor.can_emergency_vehicle:
            reasons.append("Shift requires emergency vehicle capability but doctor lacks it")

    async def _check_years_experience(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        if shift.min_years_experience > 0 and doctor.years_experience < shift.min_years_experience:
            reasons.append(
                f"Doctor has {doctor.years_experience} years experience, "
                f"shift requires {shift.min_years_experience}"
            )

    async def _check_monthly_shift_limit(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        if doctor.max_shifts_per_month >= 20:
            return  # Default value, skip check
        count = await self.assignment_repo.count_shifts_in_month(
            doctor.id, shift.date.year, shift.date.month
        )
        if count >= doctor.max_shifts_per_month:
            reasons.append(
                f"Monthly shift limit reached: {count}/{doctor.max_shifts_per_month} for "
                f"{shift.date.year}-{shift.date.month:02d}"
            )

    async def _check_night_shift_limit_personal(self, doctor: Doctor, shift: Shift, reasons: list[str]) -> None:
        if not shift.is_night or doctor.max_night_shifts_per_month is None:
            return
        count = await self.assignment_repo.count_night_shifts_in_month(
            doctor.id, shift.date.year, shift.date.month
        )
        if count >= doctor.max_night_shifts_per_month:
            reasons.append(
                f"Personal night shift limit reached: {count}/{doctor.max_night_shifts_per_month} for "
                f"{shift.date.year}-{shift.date.month:02d}"
            )
