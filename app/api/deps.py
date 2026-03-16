from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.assignment import AssignmentService
from app.services.availability import AvailabilityService
from app.services.doctor import DoctorService
from app.services.institution import InstitutionService
from app.services.shift import ShiftService

DbSession = Annotated[AsyncSession, Depends(get_session)]


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
