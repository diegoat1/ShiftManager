import uuid
from datetime import datetime

from pydantic import BaseModel

from app.utils.enums import AssignmentStatus


class AssignmentCreate(BaseModel):
    shift_id: uuid.UUID
    doctor_id: uuid.UUID
    pay_amount: float | None = None


class AssignmentRead(BaseModel):
    id: uuid.UUID
    shift_id: uuid.UUID
    doctor_id: uuid.UUID
    status: AssignmentStatus
    pay_amount: float
    assigned_at: datetime
    responded_at: datetime | None


class EligibilityResult(BaseModel):
    is_eligible: bool
    reasons: list[str] = []
    warnings: list[str] = []


class EligibleDoctorRead(BaseModel):
    doctor_id: uuid.UUID
    first_name: str
    last_name: str
    eligibility: EligibilityResult
