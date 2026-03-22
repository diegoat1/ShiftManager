import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.doctor import Doctor
from app.models.user import User
from app.repositories.doctor import DoctorRepository
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest
from app.utils.enums import UserRole


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.doctor_repo = DoctorRepository(session)

    async def login(self, data: LoginRequest) -> LoginResponse:
        user = await self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.password_hash):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is deactivated")

        user.last_login_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.commit()

        token = create_access_token(str(user.id))
        return LoginResponse(access_token=token)

    async def register(self, data: RegisterRequest) -> LoginResponse:
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise ValueError("Email already registered")

        user = await self.user_repo.create(
            email=data.email,
            password_hash=hash_password(data.password),
            role=data.role,
        )

        # If registering as medico, create linked doctor profile
        if data.role == UserRole.MEDICO:
            if not data.fiscal_code or not data.first_name or not data.last_name:
                raise ValueError("fiscal_code, first_name, and last_name are required for medico registration")

            doctor = Doctor(
                user_id=user.id,
                fiscal_code=data.fiscal_code,
                first_name=data.first_name,
                last_name=data.last_name,
                email=data.email,
                phone=data.phone,
                password_hash=user.password_hash,
            )
            self.session.add(doctor)
            await self.session.flush()

        await self.session.commit()

        token = create_access_token(str(user.id))
        return LoginResponse(access_token=token)

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        return await self.user_repo.get_by_id(user_id)
