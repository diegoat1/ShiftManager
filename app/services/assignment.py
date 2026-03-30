import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import ShiftAssignment
from app.repositories.assignment import AssignmentRepository
from app.repositories.doctor import DoctorRepository
from app.repositories.shift import ShiftRepository
from app.rules.eligibility import EligibilityEngine
from app.rules.scoring import MatchScorer
from app.schemas.assignment import AssignmentCreate, EligibilityResult
from app.utils.enums import AssignmentStatus, ShiftStatus


class AssignmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AssignmentRepository(session)
        self.shift_repo = ShiftRepository(session)
        self.doctor_repo = DoctorRepository(session)
        self.engine = EligibilityEngine(session)
        self.scorer = MatchScorer(session)

    async def assign(self, data: AssignmentCreate) -> tuple[ShiftAssignment | None, EligibilityResult]:
        # Check eligibility first
        is_eligible, reasons, warnings = await self.engine.check(data.doctor_id, data.shift_id)
        result = EligibilityResult(is_eligible=is_eligible, reasons=reasons, warnings=warnings)

        if not is_eligible:
            return None, result

        # Check not already assigned
        existing = await self.repo.get_existing(data.shift_id, data.doctor_id)
        if existing:
            return None, EligibilityResult(
                is_eligible=False, reasons=["Doctor already assigned to this shift"]
            )

        # Calculate pay
        shift = await self.shift_repo.get_by_id(data.shift_id)
        pay = data.pay_amount if data.pay_amount is not None else (shift.base_pay * shift.urgent_multiplier)

        assignment = await self.repo.create(
            shift_id=data.shift_id,
            doctor_id=data.doctor_id,
            status=AssignmentStatus.PROPOSED,
            pay_amount=pay,
        )

        # Update shift status
        active_count = await self.repo.count_active_for_shift(data.shift_id)
        if active_count >= shift.required_doctors:
            await self.shift_repo.update(shift, status=ShiftStatus.FILLED)
        elif active_count > 0:
            await self.shift_repo.update(shift, status=ShiftStatus.PARTIALLY_FILLED)

        await self.session.commit()
        return assignment, result

    async def unassign(self, assignment_id: uuid.UUID) -> bool:
        assignment = await self.repo.get_by_id(assignment_id)
        if not assignment:
            return False
        await self.repo.update(assignment, status=AssignmentStatus.CANCELLED)

        # Update shift status
        shift = await self.shift_repo.get_by_id(assignment.shift_id)
        active_count = await self.repo.count_active_for_shift(assignment.shift_id)
        if active_count == 0:
            await self.shift_repo.update(shift, status=ShiftStatus.OPEN)
        elif active_count < shift.required_doctors:
            await self.shift_repo.update(shift, status=ShiftStatus.PARTIALLY_FILLED)

        await self.session.commit()
        return True

    async def check_eligibility(self, doctor_id: uuid.UUID, shift_id: uuid.UUID) -> EligibilityResult:
        is_eligible, reasons, warnings = await self.engine.check(doctor_id, shift_id)
        return EligibilityResult(is_eligible=is_eligible, reasons=reasons, warnings=warnings)

    async def get_eligible_doctors(self, shift_id: uuid.UUID) -> list[dict]:
        doctors = await self.doctor_repo.get_all(limit=1000, is_active=True)
        shift = await self.shift_repo.get_with_requirements(shift_id)

        eligible_ids = []
        all_results = []
        for doctor in doctors:
            is_eligible, reasons, warnings = await self.engine.check(doctor.id, shift_id)
            all_results.append({
                "doctor": doctor,
                "is_eligible": is_eligible,
                "eligibility": EligibilityResult(
                    is_eligible=is_eligible, reasons=reasons, warnings=warnings
                ),
            })
            if is_eligible:
                eligible_ids.append(doctor.id)

        # Score eligible doctors
        scored_map: dict = {}
        if shift and eligible_ids:
            scored_list = await self.scorer.score_many(eligible_ids, shift)
            scored_map = {s.doctor_id: s for s in scored_list}

        # Build response: eligible first (sorted by score desc), then ineligible
        eligible_out = []
        ineligible_out = []
        for item in all_results:
            doctor = item["doctor"]
            scored = scored_map.get(doctor.id)
            entry = {
                "doctor_id": doctor.id,
                "first_name": doctor.first_name,
                "last_name": doctor.last_name,
                "eligibility": item["eligibility"],
                "score": scored.score if scored else 0,
                "rank": 0,
                "breakdown": scored.breakdown.to_dict() if scored else None,
                "distance_km": scored.distance_km if scored else None,
                "certifications": scored.certifications if scored else [],
                "languages": scored.languages if scored else [],
                "years_experience": scored.years_experience if scored else 0,
                "can_work_alone": scored.can_work_alone if scored else False,
                "can_emergency_vehicle": scored.can_emergency_vehicle if scored else False,
            }
            if item["is_eligible"]:
                eligible_out.append(entry)
            else:
                ineligible_out.append(entry)

        # Sort eligible by score desc, assign ranks
        eligible_out.sort(key=lambda x: x["score"], reverse=True)
        for i, entry in enumerate(eligible_out):
            entry["rank"] = i + 1

        return eligible_out + ineligible_out

    async def self_apply(
        self, doctor_id: uuid.UUID, shift_id: uuid.UUID,
    ) -> tuple[ShiftAssignment | None, EligibilityResult]:
        """Doctor self-applies to a shift. Single transaction."""
        from app.models.assignment import ASSIGNMENT_SOURCE_SELF_APPLIED
        from app.repositories.offer import OfferRepository

        # Check pending offer
        offer_repo = OfferRepository(self.session)
        existing_offer = await offer_repo.get_existing(shift_id, doctor_id)
        if existing_offer and existing_offer.status in ('proposed', 'viewed'):
            return None, EligibilityResult(
                is_eligible=False,
                reasons=["Hai gia un'offerta pendente per questo turno. Rispondi all'offerta."],
            )

        # Check not already assigned
        existing = await self.repo.get_existing(shift_id, doctor_id)
        if existing:
            return None, EligibilityResult(
                is_eligible=False, reasons=["Gia candidato a questo turno"],
            )

        # Check shift is still open
        shift = await self.shift_repo.get_by_id(shift_id)
        if not shift or shift.status not in (ShiftStatus.OPEN, ShiftStatus.PARTIALLY_FILLED):
            return None, EligibilityResult(
                is_eligible=False, reasons=["Il turno non e piu disponibile"],
            )

        # Eligibility check
        is_eligible, reasons, warnings = await self.engine.check(doctor_id, shift_id)
        result = EligibilityResult(is_eligible=is_eligible, reasons=reasons, warnings=warnings)
        if not is_eligible:
            return None, result

        # Create assignment with source in single transaction
        pay = shift.base_pay * shift.urgent_multiplier
        assignment = await self.repo.create(
            shift_id=shift_id,
            doctor_id=doctor_id,
            status=AssignmentStatus.PROPOSED,
            pay_amount=pay,
            source=ASSIGNMENT_SOURCE_SELF_APPLIED,
        )

        # Update shift status
        active_count = await self.repo.count_active_for_shift(shift_id)
        if active_count >= shift.required_doctors:
            await self.shift_repo.update(shift, status=ShiftStatus.FILLED)
        elif active_count > 0:
            await self.shift_repo.update(shift, status=ShiftStatus.PARTIALLY_FILLED)

        await self.session.commit()
        return assignment, result

    async def get_available_shifts_for_doctor(
        self,
        doctor_id: uuid.UUID,
        start,
        end,
        institution_type: str | None = None,
        is_night: bool | None = None,
    ) -> list[dict]:
        """Get open/partially_filled shifts with eligibility + score for the doctor."""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.models.institution import InstitutionSite
        from app.models.shift import Shift, ShiftLanguageRequirement, ShiftRequirement
        from app.repositories.offer import OfferRepository

        stmt = (
            select(Shift)
            .options(
                selectinload(Shift.site).selectinload(InstitutionSite.institution),
                selectinload(Shift.requirements).selectinload(ShiftRequirement.certification_type),
                selectinload(Shift.language_requirements).selectinload(ShiftLanguageRequirement.language),
            )
            .where(
                Shift.status.in_([ShiftStatus.OPEN, ShiftStatus.PARTIALLY_FILLED]),
                Shift.date >= start,
                Shift.date <= end,
            )
            .order_by(Shift.date.asc(), Shift.start_datetime.asc())
            .limit(200)
        )
        if is_night is not None:
            stmt = stmt.where(Shift.is_night == is_night)

        result = await self.session.execute(stmt)
        shifts = result.scalars().unique().all()

        # Post-query filter by institution_type
        if institution_type:
            shifts = [
                s for s in shifts
                if s.site and s.site.institution
                and s.site.institution.institution_type == institution_type
            ]

        offer_repo = OfferRepository(self.session)
        out = []
        for shift in shifts:
            is_eligible, reasons, warnings = await self.engine.check(doctor_id, shift.id)
            scored = await self.scorer.score(doctor_id, shift)
            existing_assignment = await self.repo.get_existing(shift.id, doctor_id)
            existing_offer = await offer_repo.get_existing(shift.id, doctor_id)

            site = shift.site
            institution = site.institution if site else None
            out.append({
                "id": shift.id,
                "site_id": shift.site_id,
                "date": shift.date,
                "start_datetime": shift.start_datetime,
                "end_datetime": shift.end_datetime,
                "required_doctors": shift.required_doctors,
                "status": shift.status.value if hasattr(shift.status, 'value') else str(shift.status),
                "base_pay": shift.base_pay,
                "urgent_multiplier": shift.urgent_multiplier,
                "is_night": shift.is_night,
                "shift_type": shift.shift_type,
                "min_years_experience": shift.min_years_experience,
                "requires_independent_work": shift.requires_independent_work,
                "requires_emergency_vehicle": shift.requires_emergency_vehicle,
                "site_name": site.name if site else None,
                "site_city": site.city if site else None,
                "institution_name": institution.name if institution else None,
                "institution_type": institution.institution_type if institution else None,
                "eligibility": EligibilityResult(
                    is_eligible=is_eligible, reasons=reasons, warnings=warnings,
                ),
                "score": scored.score,
                "score_breakdown": scored.breakdown.to_dict() if scored and scored.breakdown else None,
                "already_applied": existing_assignment is not None,
                "has_pending_offer": (
                    existing_offer is not None
                    and existing_offer.status in ('proposed', 'viewed')
                ),
            })
        return out

    async def get_by_shift(self, shift_id: uuid.UUID):
        return await self.repo.get_by_shift(shift_id)

    async def get_by_doctor(self, doctor_id: uuid.UUID):
        return await self.repo.get_by_doctor(doctor_id)
