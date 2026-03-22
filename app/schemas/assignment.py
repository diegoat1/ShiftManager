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


class ScoreBreakdownRead(BaseModel):
    availability: int
    shift_preference: int
    site_affinity: int
    workload_balance: int
    distance: int
    extra_qualifications: int
    reliability: int = 0
    fairness: int = 0
    cost_efficiency: int = 0


class ScoredEligibleDoctorRead(BaseModel):
    doctor_id: uuid.UUID
    first_name: str
    last_name: str
    eligibility: EligibilityResult
    score: int = 0
    rank: int = 0
    breakdown: ScoreBreakdownRead | None = None
    distance_km: float | None = None
    certifications: list[str] = []
    languages: list[str] = []
    years_experience: int = 0
    can_work_alone: bool = False
    can_emergency_vehicle: bool = False
