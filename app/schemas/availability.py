import uuid
from datetime import date, time

from pydantic import BaseModel

from app.utils.enums import AvailabilityType, UnavailabilityReason


class AvailabilityCreate(BaseModel):
    date: date
    start_time: time
    end_time: time
    availability_type: AvailabilityType = AvailabilityType.AVAILABLE


class BulkAvailabilityCreate(BaseModel):
    entries: list[AvailabilityCreate]


class AvailabilityRead(BaseModel):
    id: int
    doctor_id: uuid.UUID
    date: date
    start_time: time
    end_time: time
    availability_type: AvailabilityType


class UnavailabilityCreate(BaseModel):
    start_date: date
    end_date: date
    reason: UnavailabilityReason = UnavailabilityReason.OTHER


class UnavailabilityRead(BaseModel):
    id: int
    doctor_id: uuid.UUID
    start_date: date
    end_date: date
    reason: UnavailabilityReason
    is_approved: bool
