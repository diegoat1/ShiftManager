import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import ShiftAssignment
from app.repositories.assignment import AssignmentRepository
from app.repositories.doctor import DoctorRepository
from app.repositories.shift import ShiftRepository
from app.rules.eligibility import EligibilityEngine
from app.schemas.assignment import AssignmentCreate, EligibilityResult
from app.utils.enums import AssignmentStatus, ShiftStatus


class AssignmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AssignmentRepository(session)
        self.shift_repo = ShiftRepository(session)
        self.doctor_repo = DoctorRepository(session)
        self.engine = EligibilityEngine(session)

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
        eligible = []
        for doctor in doctors:
            is_eligible, reasons, warnings = await self.engine.check(doctor.id, shift_id)
            eligible.append({
                "doctor_id": doctor.id,
                "first_name": doctor.first_name,
                "last_name": doctor.last_name,
                "eligibility": EligibilityResult(
                    is_eligible=is_eligible, reasons=reasons, warnings=warnings
                ),
            })
        return eligible

    async def get_by_shift(self, shift_id: uuid.UUID):
        return await self.repo.get_by_shift(shift_id)

    async def get_by_doctor(self, doctor_id: uuid.UUID):
        return await self.repo.get_by_doctor(doctor_id)
