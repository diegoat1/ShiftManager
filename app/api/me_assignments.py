from datetime import date, datetime, timezone

from fastapi import APIRouter, Query

from app.api.deps import CurrentDoctor, DbSession
from app.repositories.assignment import AssignmentRepository
from app.schemas.assignment import MyAssignmentRead
from app.utils.enums import AssignmentStatus

router = APIRouter(prefix="/me", tags=["me-assignments"])


def _to_my_assignment(a) -> MyAssignmentRead:
    shift = a.shift
    site = shift.site if shift else None
    institution = site.institution if site else None
    start = shift.start_datetime if shift else a.assigned_at
    end = shift.end_datetime if shift else a.assigned_at
    duration = (end - start).total_seconds() / 3600 if start and end else 0

    return MyAssignmentRead(
        id=a.id,
        shift_id=a.shift_id,
        status=a.status,
        pay_amount=a.pay_amount,
        assigned_at=a.assigned_at,
        shift_date=shift.date if shift else a.assigned_at.date(),
        start_datetime=start,
        end_datetime=end,
        duration_hours=round(duration, 1),
        shift_type=shift.shift_type if shift else None,
        is_night=shift.is_night if shift else False,
        site_name=site.name if site else None,
        site_city=site.city if site else None,
        institution_name=institution.name if institution else None,
        source=getattr(a, 'source', None),
    )


@router.get("/assignments", response_model=list[MyAssignmentRead])
async def get_my_assignments(
    doctor: CurrentDoctor,
    session: DbSession,
    start: date | None = None,
    end: date | None = None,
    statuses: list[AssignmentStatus] | None = Query(None),
):
    repo = AssignmentRepository(session)
    start_dt = datetime.combine(start, datetime.min.time()) if start else None
    end_dt = datetime.combine(end, datetime.max.time()) if end else None

    assignments = await repo.get_by_doctor_with_details(
        doctor_id=doctor.id,
        start=start_dt,
        end=end_dt,
        statuses=statuses,
    )
    return [_to_my_assignment(a) for a in assignments]
