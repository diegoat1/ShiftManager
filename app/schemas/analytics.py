import uuid
from datetime import datetime

from pydantic import BaseModel


class KPIResponse(BaseModel):
    total_shifts: int = 0
    covered_shifts: int = 0
    coverage_percent: float = 0.0
    avg_fill_time_hours: float | None = None
    total_offers_sent: int = 0
    acceptance_rate: float = 0.0
    active_doctors: int = 0
    total_assignments: int = 0


class MonthlyKPI(BaseModel):
    month: str
    total_shifts: int = 0
    covered_shifts: int = 0
    coverage_percent: float = 0.0
    offers_sent: int = 0
    acceptance_rate: float = 0.0


class DoctorStatsRead(BaseModel):
    doctor_id: uuid.UUID
    first_name: str
    last_name: str
    total_offers_received: int = 0
    total_offers_accepted: int = 0
    total_offers_rejected: int = 0
    total_offers_expired: int = 0
    total_cancellations: int = 0
    avg_response_time_minutes: float = 0.0
    acceptance_rate: float = 0.0
    reliability_score: float = 0.0
    last_calculated_at: datetime | None = None


class AuditLogRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: str
    entity_type: str
    entity_id: str
    old_values: str | None = None
    new_values: str | None = None
    ip_address: str | None = None
    created_at: datetime
