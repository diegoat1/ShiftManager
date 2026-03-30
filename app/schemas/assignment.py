import uuid
from datetime import date, datetime

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


class MyAssignmentRead(BaseModel):
    id: uuid.UUID
    shift_id: uuid.UUID
    status: AssignmentStatus
    pay_amount: float | None = None
    assigned_at: datetime
    shift_date: date
    start_datetime: datetime
    end_datetime: datetime
    duration_hours: float
    shift_type: str | None = None
    is_night: bool = False
    site_name: str | None = None
    site_city: str | None = None
    institution_name: str | None = None
    source: str | None = None


class CandidatureCreate(BaseModel):
    shift_id: uuid.UUID


class AvailableShiftRead(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    date: date
    start_datetime: datetime
    end_datetime: datetime
    required_doctors: int
    status: str
    base_pay: float
    urgent_multiplier: float
    is_night: bool
    shift_type: str | None = None
    min_years_experience: int = 0
    requires_independent_work: bool = False
    requires_emergency_vehicle: bool = False
    site_name: str | None = None
    site_city: str | None = None
    institution_name: str | None = None
    institution_type: str | None = None
    eligibility: "EligibilityResult"
    score: int = 0
    score_breakdown: "ScoreBreakdownRead | None" = None
    already_applied: bool = False
    has_pending_offer: bool = False


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


# Resolve forward references
AvailableShiftRead.model_rebuild()
