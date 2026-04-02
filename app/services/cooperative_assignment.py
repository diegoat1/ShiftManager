import uuid
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cooperative import CooperativeSiteAssignment
from app.repositories.cooperative import CooperativeRepository
from app.repositories.institution import InstitutionRepository
from app.utils.dates import utcnow_naive


class CooperativeSiteAssignmentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = CooperativeRepository(session)
        self.inst_repo = InstitutionRepository(session)

    async def assign(
        self,
        cooperative_id: uuid.UUID,
        site_id: uuid.UUID,
        start_date: date,
        end_date: date | None = None,
        notes: str | None = None,
    ) -> CooperativeSiteAssignment:
        # Validate entities exist
        coop = await self.repo.get_by_id(cooperative_id)
        if not coop:
            raise ValueError(f"Cooperative {cooperative_id} not found")
        site = await self.inst_repo.get_site(site_id)
        if not site:
            raise ValueError(f"Site {site_id} not found")

        # Range validation
        if end_date is not None and end_date < start_date:
            raise ValueError("end_date must be >= start_date")

        # Overlap check
        overlap = await self.repo.check_overlap(site_id, start_date, end_date)
        if overlap:
            raise ValueError(
                f"Overlapping assignment exists for site {site_id}: "
                f"{overlap.start_date} – {overlap.end_date or 'ongoing'} "
                f"(cooperative {overlap.cooperative_id})"
            )

        return await self.repo.create_assignment(
            cooperative_id=cooperative_id,
            site_id=site_id,
            start_date=start_date,
            end_date=end_date,
            notes=notes,
        )

    async def update(
        self,
        assignment_id: uuid.UUID,
        end_date: date | None = ...,
        notes: str | None = ...,
    ) -> CooperativeSiteAssignment:
        assignment = await self.repo.get_assignment(assignment_id)
        if not assignment:
            raise ValueError(f"Assignment {assignment_id} not found")

        if end_date is not ...:
            if end_date is not None and end_date < assignment.start_date:
                raise ValueError("end_date must be >= start_date")
            # Re-validate overlap if changing dates
            overlap = await self.repo.check_overlap(
                assignment.site_id, assignment.start_date, end_date,
                exclude_id=assignment.id,
            )
            if overlap:
                raise ValueError(
                    f"Update would overlap with assignment {overlap.id}: "
                    f"{overlap.start_date} – {overlap.end_date or 'ongoing'}"
                )
            assignment.end_date = end_date

        if notes is not ...:
            assignment.notes = notes

        await self.session.flush()
        await self.session.refresh(assignment)
        return assignment

    async def deactivate(self, assignment_id: uuid.UUID) -> CooperativeSiteAssignment:
        """End an ongoing assignment by setting end_date to today."""
        assignment = await self.repo.get_assignment(assignment_id)
        if not assignment:
            raise ValueError(f"Assignment {assignment_id} not found")
        if assignment.end_date is not None:
            raise ValueError("Assignment already has an end date")
        assignment.end_date = utcnow_naive().date()
        await self.session.flush()
        await self.session.refresh(assignment)
        return assignment

    async def get_active_for_site(
        self, site_id: uuid.UUID
    ) -> CooperativeSiteAssignment | None:
        return await self.repo.get_active_for_site(site_id)

    async def get_history_for_site(
        self, site_id: uuid.UUID
    ) -> list[CooperativeSiteAssignment]:
        return await self.repo.get_history_for_site(site_id)

    async def get_sites_for_cooperative(
        self, cooperative_id: uuid.UUID, active_only: bool = True
    ) -> list[CooperativeSiteAssignment]:
        return await self.repo.get_assignments_for_cooperative(
            cooperative_id, active_only=active_only
        )
