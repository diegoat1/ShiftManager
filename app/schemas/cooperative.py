import uuid
from datetime import date, datetime

from pydantic import BaseModel, model_validator


class CooperativeCreate(BaseModel):
    name: str
    partita_iva: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None


class CooperativeUpdate(BaseModel):
    name: str | None = None
    partita_iva: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class CooperativeRead(BaseModel):
    id: uuid.UUID
    name: str
    partita_iva: str | None
    address: str | None
    city: str | None
    province: str | None
    email: str | None
    phone: str | None
    notes: str | None
    is_active: bool
    created_at: datetime


class CooperativeBrief(BaseModel):
    id: uuid.UUID
    name: str
    partita_iva: str | None
    is_active: bool


# --- Site assignments ---

class SiteAssignmentCreate(BaseModel):
    site_id: uuid.UUID
    start_date: date
    end_date: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def end_after_start(self):
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be >= start_date")
        return self


class SiteAssignmentUpdate(BaseModel):
    end_date: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def end_not_none_check(self):
        # end_date validation happens in service (needs start_date from DB)
        return self


class SiteAssignmentRead(BaseModel):
    id: uuid.UUID
    cooperative_id: uuid.UUID
    site_id: uuid.UUID
    start_date: date
    end_date: date | None
    notes: str | None
    created_at: datetime
