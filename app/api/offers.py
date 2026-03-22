import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import RequireAdmin, get_offer_service, get_assignment_service
from app.schemas.offer import OfferBatchCreate, OfferCreate, OfferRead
from app.services.assignment import AssignmentService
from app.services.offer import OfferService

router = APIRouter(prefix="/shifts/{shift_id}/offers", tags=["offers"])

OfferSvc = Annotated[OfferService, Depends(get_offer_service)]
AssignSvc = Annotated[AssignmentService, Depends(get_assignment_service)]


def _offer_to_read(offer) -> OfferRead:
    doctor_name = None
    if hasattr(offer, 'doctor') and offer.doctor:
        doctor_name = f"{offer.doctor.first_name} {offer.doctor.last_name}"
    shift_date = None
    site_name = None
    if hasattr(offer, 'shift') and offer.shift:
        shift_date = str(offer.shift.date)
        if offer.shift.site:
            site_name = offer.shift.site.name
    return OfferRead(
        id=offer.id,
        shift_id=offer.shift_id,
        doctor_id=offer.doctor_id,
        status=offer.status,
        offered_at=offer.offered_at,
        expires_at=offer.expires_at,
        responded_at=offer.responded_at,
        response_note=offer.response_note,
        rank_snapshot=offer.rank_snapshot,
        score_snapshot=offer.score_snapshot,
        doctor_name=doctor_name,
        shift_date=shift_date,
        site_name=site_name,
    )


@router.post("/send", response_model=OfferRead, status_code=201)
async def send_offer(shift_id: uuid.UUID, data: OfferCreate, admin: RequireAdmin, svc: OfferSvc):
    try:
        offer = await svc.send_offer(
            shift_id=shift_id,
            doctor_id=data.doctor_id,
            expires_in_hours=data.expires_in_hours,
            proposed_by=admin.id,
        )
        return _offer_to_read(offer)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/send-batch", response_model=list[OfferRead], status_code=201)
async def send_batch_offers(
    shift_id: uuid.UUID,
    data: OfferBatchCreate,
    admin: RequireAdmin,
    svc: OfferSvc,
    assign_svc: AssignSvc,
):
    doctor_ids = data.doctor_ids
    if not doctor_ids:
        # Auto-select top N eligible doctors
        eligible = await assign_svc.get_eligible_doctors(shift_id)
        eligible_only = []
        for e in eligible:
            elig = e.get("eligibility")
            if isinstance(elig, dict) and elig.get("is_eligible"):
                eligible_only.append(e)
            elif hasattr(elig, "is_eligible") and elig.is_eligible:
                eligible_only.append(e)
        doctor_ids = [e["doctor_id"] for e in eligible_only[:data.top_n]]

    if not doctor_ids:
        raise HTTPException(400, "No eligible doctors found")

    offers = await svc.send_batch(
        shift_id=shift_id,
        doctor_ids=doctor_ids,
        expires_in_hours=data.expires_in_hours,
        proposed_by=admin.id,
    )
    return [_offer_to_read(o) for o in offers]


@router.get("/", response_model=list[OfferRead])
async def list_shift_offers(shift_id: uuid.UUID, admin: RequireAdmin, svc: OfferSvc):
    offers = await svc.get_by_shift(shift_id)
    return [_offer_to_read(o) for o in offers]


@router.post("/{offer_id}/cancel", response_model=OfferRead)
async def cancel_offer(shift_id: uuid.UUID, offer_id: uuid.UUID, admin: RequireAdmin, svc: OfferSvc):
    try:
        offer = await svc.cancel(offer_id)
        if not offer:
            raise HTTPException(404, "Offer not found")
        return _offer_to_read(offer)
    except ValueError as e:
        raise HTTPException(400, str(e))
