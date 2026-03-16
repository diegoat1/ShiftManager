import uuid
from datetime import date, datetime, time

from pydantic import BaseModel

from app.utils.enums import ShiftStatus


class TemplateCreate(BaseModel):
    site_id: uuid.UUID
    name: str
    start_time: time
    end_time: time
    required_doctors: int = 1
    base_pay: float = 0.0
    is_night: bool = False


class TemplateRead(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    name: str
    start_time: time
    end_time: time
    required_doctors: int
    base_pay: float
    is_night: bool


class ShiftCreate(BaseModel):
    site_id: uuid.UUID
    template_id: uuid.UUID | None = None
    date: date
    start_datetime: datetime
    end_datetime: datetime
    required_doctors: int = 1
    base_pay: float = 0.0
    urgent_multiplier: float = 1.0
    is_night: bool = False
    shift_type: str | None = None
    priority: int = 3
    min_code_level_id: int | None = None
    requires_independent_work: bool = False
    requires_emergency_vehicle: bool = False
    min_years_experience: int = 0


class ShiftUpdate(BaseModel):
    required_doctors: int | None = None
    status: ShiftStatus | None = None
    base_pay: float | None = None
    urgent_multiplier: float | None = None
    shift_type: str | None = None
    priority: int | None = None
    min_code_level_id: int | None = None
    requires_independent_work: bool | None = None
    requires_emergency_vehicle: bool | None = None
    min_years_experience: int | None = None


class ShiftRequirementCreate(BaseModel):
    certification_type_id: int
    is_mandatory: bool = True


class ShiftLanguageRequirementCreate(BaseModel):
    language_id: int
    min_proficiency: int = 3


class ShiftRead(BaseModel):
    id: uuid.UUID
    site_id: uuid.UUID
    template_id: uuid.UUID | None
    date: date
    start_datetime: datetime
    end_datetime: datetime
    required_doctors: int
    status: ShiftStatus
    base_pay: float
    urgent_multiplier: float
    is_night: bool
    shift_type: str | None
    priority: int
    min_code_level_id: int | None
    requires_independent_work: bool
    requires_emergency_vehicle: bool
    min_years_experience: int
    created_at: datetime


class GenerateShiftsRequest(BaseModel):
    site_id: uuid.UUID
    template_ids: list[uuid.UUID]
    start_date: date
    end_date: date
