import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import decode_access_token, oauth2_scheme
from app.models.doctor import Doctor
from app.models.user import User
from app.repositories.doctor import DoctorRepository
from app.repositories.user import UserRepository
from app.services.analytics import AnalyticsService
from app.services.message import MessageService
from app.services.assignment import AssignmentService
from app.services.audit import AuditService
from app.services.auth import AuthService
from app.services.availability import AvailabilityService
from app.services.cooperative_assignment import CooperativeSiteAssignmentService
from app.services.doctor import DoctorService
from app.services.document import DocumentService
from app.services.institution import InstitutionService
from app.services.notification import NotificationService
from app.services.offer import OfferService
from app.services.reliability import ReliabilityService
from app.services.shift import ShiftService
from app.utils.enums import UserRole

DbSession = Annotated[AsyncSession, Depends(get_session)]


# --- Auth dependencies ---

async def get_current_user_optional(
    session: DbSession,
    token: str | None = Depends(oauth2_scheme),
) -> User | None:
    if not token:
        return None
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
    except JWTError:
        return None
    repo = UserRepository(session)
    user = await repo.get_by_id(uuid.UUID(user_id))
    if user and not user.is_active:
        return None
    return user


async def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]


def require_role(*roles: UserRole):
    allowed_values = {r.value for r in roles}

    async def checker(user: CurrentUser) -> User:
        role_value = user.role.value if isinstance(user.role, UserRole) else str(user.role)
        if role_value not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {role_value} not authorized. Required: {list(allowed_values)}",
            )
        return user
    return checker


ADMIN_ROLES = (UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.COORDINATORE)
RequireAdmin = Annotated[User, Depends(require_role(UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.COORDINATORE))]


async def get_current_doctor(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Doctor:
    role_value = user.role.value if isinstance(user.role, UserRole) else str(user.role)
    if role_value != UserRole.MEDICO.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can access this resource",
        )
    from sqlalchemy import select
    result = await session.execute(select(Doctor).where(Doctor.user_id == user.id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found",
        )
    repo = DoctorRepository(session)
    doctor = await repo.get_with_relations(doc.id)
    return doctor


CurrentDoctor = Annotated[Doctor, Depends(get_current_doctor)]


# --- Service factories ---

async def get_doctor_service(session: DbSession) -> DoctorService:
    return DoctorService(session)


async def get_institution_service(session: DbSession) -> InstitutionService:
    return InstitutionService(session)


async def get_shift_service(session: DbSession) -> ShiftService:
    return ShiftService(session)


async def get_availability_service(session: DbSession) -> AvailabilityService:
    return AvailabilityService(session)


async def get_assignment_service(session: DbSession) -> AssignmentService:
    return AssignmentService(session)


async def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(session)


async def get_document_service(session: DbSession) -> DocumentService:
    return DocumentService(session)


async def get_offer_service(session: DbSession) -> OfferService:
    return OfferService(session)


async def get_notification_service(session: DbSession) -> NotificationService:
    return NotificationService(session)


async def get_audit_service(session: DbSession) -> AuditService:
    return AuditService(session)


async def get_reliability_service(session: DbSession) -> ReliabilityService:
    return ReliabilityService(session)


async def get_analytics_service(session: DbSession) -> AnalyticsService:
    return AnalyticsService(session)


async def get_message_service(session: DbSession) -> MessageService:
    return MessageService(session)


async def get_cooperative_assignment_service(session: DbSession) -> CooperativeSiteAssignmentService:
    return CooperativeSiteAssignmentService(session)
