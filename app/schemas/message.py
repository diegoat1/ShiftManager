import uuid
from datetime import datetime

from pydantic import BaseModel, constr


class MessageCreate(BaseModel):
    body: constr(min_length=1, max_length=5000)


class MessageRead(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    recipient_id: uuid.UUID
    body: str
    sent_at: datetime
    read_at: datetime | None = None


class ConversationSummary(BaseModel):
    user_id: uuid.UUID
    user_name: str
    user_email: str
    user_role: str
    last_message: str
    last_message_at: datetime
    unread_count: int


class ContactRead(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    role: str


class UnreadMessagesCountResponse(BaseModel):
    count: int
