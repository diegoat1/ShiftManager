from fastapi import APIRouter

from app.api import assignments, availability, doctors, institutions, lookups, shifts

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(doctors.router)
api_router.include_router(institutions.router)
api_router.include_router(shifts.router)
api_router.include_router(availability.router)
api_router.include_router(assignments.router)
api_router.include_router(lookups.router)
