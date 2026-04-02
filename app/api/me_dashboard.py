from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentDoctor, DbSession, get_offer_service
from app.utils.dates import utcnow_naive
from app.api.me_assignments import _to_my_assignment
from app.api.me_offers import _offer_to_read
from app.models.doctor import DoctorCertification
from app.models.document import Document, DocumentType
from app.repositories.assignment import AssignmentRepository
from app.schemas.me_dashboard import (
    ExpiringCertRead,
    MeDashboardResponse,
    MissingDocRead,
)
from app.services.offer import OfferService
from app.utils.enums import AssignmentStatus

router = APIRouter(prefix="/me", tags=["me-dashboard"])


@router.get("/dashboard", response_model=MeDashboardResponse)
async def get_my_dashboard(
    doctor: CurrentDoctor,
    session: DbSession,
    offer_svc: OfferService = Depends(get_offer_service),
):
    now = utcnow_naive()
    today = date.today()

    repo = AssignmentRepository(session)

    # 1. Upcoming assignments (proposed + confirmed, future, limit 5)
    upcoming = await repo.get_by_doctor_with_details(
        doctor_id=doctor.id,
        start=now,
        statuses=[AssignmentStatus.PROPOSED, AssignmentStatus.CONFIRMED],
        limit=5,
    )
    upcoming_reads = [_to_my_assignment(a) for a in upcoming]

    # 2. Pending offers
    pending_offers_raw = await offer_svc.get_pending_by_doctor(doctor.id)
    pending_offers = [_offer_to_read(o) for o in pending_offers_raw]

    # 3. Expiring certifications (within 90 days, not already expired)
    ninety_days = today + timedelta(days=90)
    cert_result = await session.execute(
        select(DoctorCertification)
        .options(selectinload(DoctorCertification.certification_type))
        .where(
            DoctorCertification.doctor_id == doctor.id,
            DoctorCertification.is_active == True,
            DoctorCertification.expiry_date != None,
            DoctorCertification.expiry_date > today,
            DoctorCertification.expiry_date <= ninety_days,
        )
    )
    expiring_certs = []
    for cert in cert_result.scalars().all():
        ct_name = cert.certification_type.name if cert.certification_type else "?"
        days_left = (cert.expiry_date - today).days
        expiring_certs.append(ExpiringCertRead(
            certification_name=ct_name,
            expiry_date=cert.expiry_date,
            days_remaining=days_left,
        ))

    # 4. Missing mandatory documents
    mandatory_types_result = await session.execute(
        select(DocumentType).where(DocumentType.is_mandatory == True)
    )
    mandatory_types = mandatory_types_result.scalars().all()

    uploaded_types_result = await session.execute(
        select(Document.document_type_id).where(Document.doctor_id == doctor.id)
    )
    uploaded_type_ids = {row[0] for row in uploaded_types_result.all()}

    missing_docs = [
        MissingDocRead(document_type_id=dt.id, document_type_name=dt.name)
        for dt in mandatory_types
        if dt.id not in uploaded_type_ids
    ]

    # 5. Month stats (confirmed + completed only)
    first_of_month = date(today.year, today.month, 1)
    if today.month == 12:
        last_of_month = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_of_month = date(today.year, today.month + 1, 1) - timedelta(days=1)

    month_assignments = await repo.get_by_doctor_with_details(
        doctor_id=doctor.id,
        start=datetime.combine(first_of_month, datetime.min.time()),
        end=datetime.combine(last_of_month, datetime.max.time()),
        statuses=[AssignmentStatus.CONFIRMED, AssignmentStatus.COMPLETED],
    )
    month_shifts_total = len(month_assignments)
    month_hours = sum(
        (a.shift.end_datetime - a.shift.start_datetime).total_seconds() / 3600
        for a in month_assignments
        if a.shift
    )

    return MeDashboardResponse(
        upcoming_assignments=upcoming_reads,
        pending_offers_count=len(pending_offers),
        pending_offers=pending_offers,
        expiring_certifications=expiring_certs,
        missing_mandatory_docs=missing_docs,
        month_shifts_total=month_shifts_total,
        month_hours_worked=round(month_hours, 1),
        profile_completion_percent=doctor.profile_completion_percent or 0,
    )
