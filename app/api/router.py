from fastapi import APIRouter

from app.api import (
    admin_documents,
    analytics,
    assignments,
    audit,
    auth,
    availability,
    doctors,
    documents,
    institutions,
    lookups,
    me,
    me_notifications,
    me_offers,
    offers,
    shifts,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(doctors.router)
api_router.include_router(institutions.router)
api_router.include_router(shifts.router)
api_router.include_router(availability.router)
api_router.include_router(assignments.router)
api_router.include_router(lookups.router)
api_router.include_router(me.router)
api_router.include_router(documents.router)
api_router.include_router(admin_documents.router)
api_router.include_router(me_offers.router)
api_router.include_router(me_notifications.router)
api_router.include_router(offers.router)
api_router.include_router(analytics.router)
api_router.include_router(audit.router)

# Auth router is mounted at root level (no /api/v1 prefix)
auth_router = auth.router
