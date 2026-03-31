import uuid
from datetime import datetime

from pydantic import BaseModel


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
