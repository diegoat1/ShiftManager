import uuid
from datetime import datetime

from pydantic import BaseModel

from app.utils.enums import OfferStatus


class OfferCreate(BaseModel):
    doctor_id: uuid.UUID
    expires_in_hours: float = 12.0


class OfferBatchCreate(BaseModel):
    doctor_ids: list[uuid.UUID] | None = None
    top_n: int = 3
    expires_in_hours: float = 12.0


class OfferRead(BaseModel):
    id: uuid.UUID
    shift_id: uuid.UUID
    doctor_id: uuid.UUID
    status: OfferStatus
    offered_at: datetime
    expires_at: datetime | None = None
    responded_at: datetime | None = None
    response_note: str | None = None
    rank_snapshot: int | None = None
    score_snapshot: int | None = None
    doctor_name: str | None = None
    shift_date: str | None = None
    site_name: str | None = None


class OfferRespond(BaseModel):
    response_note: str | None = None
