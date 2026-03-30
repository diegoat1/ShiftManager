from datetime import date

from pydantic import BaseModel

from app.schemas.assignment import MyAssignmentRead
from app.schemas.offer import OfferRead


class ExpiringCertRead(BaseModel):
    certification_name: str
    expiry_date: date
    days_remaining: int


class MissingDocRead(BaseModel):
    document_type_id: int
    document_type_name: str


class MeDashboardResponse(BaseModel):
    upcoming_assignments: list[MyAssignmentRead]
    pending_offers_count: int
    pending_offers: list[OfferRead]
    expiring_certifications: list[ExpiringCertRead]
    missing_mandatory_docs: list[MissingDocRead]
    month_shifts_total: int
    month_hours_worked: float
    profile_completion_percent: int
