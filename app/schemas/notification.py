import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationRead(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    body: str | None = None
    status: str
    sent_at: datetime
    read_at: datetime | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None


class UnreadCountResponse(BaseModel):
    count: int
