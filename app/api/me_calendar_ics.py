import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentDoctor, get_session
from app.models.doctor import Doctor
from app.repositories.assignment import AssignmentRepository
from app.utils.enums import AssignmentStatus

router = APIRouter(prefix="/me", tags=["me-calendar"])


def _ical_dt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _ical_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@router.post("/calendar-token")
async def generate_calendar_token(
    doctor: CurrentDoctor,
    session: AsyncSession = Depends(get_session),
):
    """Generate or regenerate a dedicated calendar feed token."""
    token = secrets.token_urlsafe(48)
    doctor.calendar_feed_token = token
    await session.flush()
    return {"token": token}


@router.get("/calendar-token")
async def get_calendar_token(
    doctor: CurrentDoctor,
    session: AsyncSession = Depends(get_session),
):
    """Get existing calendar feed token or return null."""
    return {"token": doctor.calendar_feed_token}


@router.get("/calendar.ics")
async def get_ical_feed(
    token: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """iCal feed using dedicated calendar token (not JWT)."""
    if not token:
        raise HTTPException(401, "Token richiesto")

    # Resolve doctor by calendar_feed_token
    result = await session.execute(
        select(Doctor).where(Doctor.calendar_feed_token == token)
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(401, "Token non valido")

    repo = AssignmentRepository(session)
    assignments = await repo.get_by_doctor_with_details(
        doctor_id=doctor.id,
        statuses=[
            AssignmentStatus.PROPOSED,
            AssignmentStatus.CONFIRMED,
            AssignmentStatus.COMPLETED,
        ],
    )

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ShiftManager//IT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:Turni - {_ical_escape(doctor.first_name)} {_ical_escape(doctor.last_name)}",
    ]

    now_stamp = _ical_dt(datetime.now(timezone.utc))

    for a in assignments:
        shift = a.shift
        if not shift:
            continue

        site = shift.site
        site_name = site.name if site else "Turno"
        city = site.city if site else ""
        location = f"{site_name}, {city}" if city else site_name

        status_map = {
            "proposed": "TENTATIVE",
            "confirmed": "CONFIRMED",
            "completed": "CONFIRMED",
        }
        status_val = a.status.value if hasattr(a.status, 'value') else str(a.status)
        ical_status = status_map.get(status_val, "TENTATIVE")

        uid = str(a.id) + "@shiftmanager"
        summary = _ical_escape(site_name) + (" (notte)" if shift.is_night else "")
        description = _ical_escape(
            f"Tipo: {shift.shift_type or 'Standard'}\n"
            f"Compenso: EUR {a.pay_amount:.0f}\n"
            f"Stato: {status_val}"
        )

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART:{_ical_dt(shift.start_datetime)}",
            f"DTEND:{_ical_dt(shift.end_datetime)}",
            f"SUMMARY:{summary}",
            f"LOCATION:{_ical_escape(location)}",
            f"STATUS:{ical_status}",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    ical_content = "\r\n".join(lines)

    return Response(
        content=ical_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=turni.ics"},
    )
