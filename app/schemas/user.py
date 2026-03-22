import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.utils.enums import UserRole


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.MEDICO


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    role: UserRole
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
