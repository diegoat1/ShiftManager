from pydantic import BaseModel, EmailStr

from app.utils.enums import UserRole


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.MEDICO
    # Doctor profile fields (for medico registration)
    fiscal_code: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
