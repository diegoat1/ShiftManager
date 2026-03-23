import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import RequireAdmin, get_analytics_service, get_reliability_service
from app.schemas.analytics import DoctorStatsRead, KPIResponse, MonthlyKPI
from app.services.analytics import AnalyticsService
from app.services.reliability import ReliabilityService

router = APIRouter(prefix="/admin/analytics", tags=["analytics"])

AnalyticsSvc = Annotated[AnalyticsService, Depends(get_analytics_service)]
ReliabilitySvc = Annotated[ReliabilityService, Depends(get_reliability_service)]


@router.get("/kpis", response_model=KPIResponse)
async def get_kpis(admin: RequireAdmin, svc: AnalyticsSvc):
    return await svc.get_kpis()


@router.get("/kpis/by-month", response_model=list[MonthlyKPI])
async def get_kpis_by_month(admin: RequireAdmin, svc: AnalyticsSvc, year: int | None = None):
    return await svc.get_kpis_by_month(year)


@router.get("/doctor-stats", response_model=list[DoctorStatsRead])
async def list_doctor_stats(admin: RequireAdmin, svc: ReliabilitySvc, skip: int = 0, limit: int = 50):
    stats = await svc.get_all_stats(skip, limit)
    results = []
    for s in stats:
        # Load doctor name
        from app.repositories.doctor import DoctorRepository
        from sqlalchemy.ext.asyncio import AsyncSession
        results.append(DoctorStatsRead(
            doctor_id=s.doctor_id,
            first_name="",
            last_name="",
            total_offers_received=s.total_offers_received,
            total_offers_accepted=s.total_offers_accepted,
            total_offers_rejected=s.total_offers_rejected,
            total_offers_expired=s.total_offers_expired,
            total_cancellations=s.total_cancellations,
            avg_response_time_minutes=s.avg_response_time_minutes,
            acceptance_rate=s.acceptance_rate,
            reliability_score=s.reliability_score,
            last_calculated_at=s.last_calculated_at,
        ))
    return results


@router.get("/doctor-stats/{doctor_id}", response_model=DoctorStatsRead)
async def get_doctor_stats(doctor_id: uuid.UUID, admin: RequireAdmin, svc: ReliabilitySvc):
    stats = await svc.get_stats(doctor_id)
    if not stats:
        raise HTTPException(404, "Stats not found for this doctor")
    return DoctorStatsRead(
        doctor_id=stats.doctor_id,
        first_name="",
        last_name="",
        total_offers_received=stats.total_offers_received,
        total_offers_accepted=stats.total_offers_accepted,
        total_offers_rejected=stats.total_offers_rejected,
        total_offers_expired=stats.total_offers_expired,
        total_cancellations=stats.total_cancellations,
        avg_response_time_minutes=stats.avg_response_time_minutes,
        acceptance_rate=stats.acceptance_rate,
        reliability_score=stats.reliability_score,
        last_calculated_at=stats.last_calculated_at,
    )


@router.post("/recalculate")
async def recalculate_reliability(
    user: RequireAdmin,
    svc: ReliabilitySvc,
):
    count = await svc.recalculate_all()
    return {"recalculated": count}
