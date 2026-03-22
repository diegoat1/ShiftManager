from datetime import datetime

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import ShiftAssignment
from app.models.doctor import Doctor
from app.models.offer import ShiftOffer
from app.models.shift import Shift
from app.schemas.analytics import KPIResponse, MonthlyKPI
from app.utils.enums import AssignmentStatus, OfferStatus, ShiftStatus


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_kpis(self) -> KPIResponse:
        # Total shifts (non-draft)
        stmt = select(func.count()).select_from(Shift).where(Shift.status != ShiftStatus.DRAFT)
        total_shifts = (await self.session.execute(stmt)).scalar_one()

        # Covered shifts (filled, in_progress, completed)
        covered_statuses = [ShiftStatus.FILLED, ShiftStatus.IN_PROGRESS, ShiftStatus.COMPLETED]
        stmt = select(func.count()).select_from(Shift).where(Shift.status.in_(covered_statuses))
        covered_shifts = (await self.session.execute(stmt)).scalar_one()

        coverage = (covered_shifts / total_shifts * 100) if total_shifts > 0 else 0

        # Total offers
        stmt = select(func.count()).select_from(ShiftOffer)
        total_offers = (await self.session.execute(stmt)).scalar_one()

        # Accepted offers
        stmt = select(func.count()).select_from(ShiftOffer).where(ShiftOffer.status == OfferStatus.ACCEPTED)
        accepted_offers = (await self.session.execute(stmt)).scalar_one()

        acceptance_rate = (accepted_offers / total_offers * 100) if total_offers > 0 else 0

        # Active doctors
        stmt = select(func.count()).select_from(Doctor).where(Doctor.is_active == True)
        active_doctors = (await self.session.execute(stmt)).scalar_one()

        # Total assignments
        stmt = select(func.count()).select_from(ShiftAssignment).where(
            ShiftAssignment.status.in_([AssignmentStatus.PROPOSED, AssignmentStatus.CONFIRMED])
        )
        total_assignments = (await self.session.execute(stmt)).scalar_one()

        return KPIResponse(
            total_shifts=total_shifts,
            covered_shifts=covered_shifts,
            coverage_percent=round(coverage, 1),
            total_offers_sent=total_offers,
            acceptance_rate=round(acceptance_rate, 1),
            active_doctors=active_doctors,
            total_assignments=total_assignments,
        )

    async def get_kpis_by_month(self, year: int | None = None) -> list[MonthlyKPI]:
        if not year:
            year = datetime.utcnow().year

        months = []
        for month in range(1, 13):
            # Shifts in month
            stmt = select(func.count()).select_from(Shift).where(
                func.extract("year", Shift.date) == year,
                func.extract("month", Shift.date) == month,
                Shift.status != ShiftStatus.DRAFT,
            )
            total = (await self.session.execute(stmt)).scalar_one()

            covered_statuses = [ShiftStatus.FILLED, ShiftStatus.IN_PROGRESS, ShiftStatus.COMPLETED]
            stmt = select(func.count()).select_from(Shift).where(
                func.extract("year", Shift.date) == year,
                func.extract("month", Shift.date) == month,
                Shift.status.in_(covered_statuses),
            )
            covered = (await self.session.execute(stmt)).scalar_one()

            months.append(MonthlyKPI(
                month=f"{year}-{month:02d}",
                total_shifts=total,
                covered_shifts=covered,
                coverage_percent=round((covered / total * 100) if total > 0 else 0, 1),
            ))

        return months
