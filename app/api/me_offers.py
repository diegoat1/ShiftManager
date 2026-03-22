import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, get_doctor_service, get_offer_service
from app.schemas.offer import OfferRead, OfferRespond
from app.services.doctor import DoctorService
from app.services.offer import OfferService
from app.utils.enums import UserRole

router = APIRouter(prefix="/me/offers", tags=["my-offers"])

OfferSvc = Annotated[OfferService, Depends(get_offer_service)]
DoctorSvc = Annotated[DoctorService, Depends(get_doctor_service)]


def _offer_to_read(offer) -> OfferRead:
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
        shift_date=shift_date,
        site_name=site_name,
    )


async def _get_doctor_id(user: CurrentUser, svc: DoctorSvc) -> uuid.UUID:
    if user.role != UserRole.MEDICO:
        raise HTTPException(403, "Only doctors can access offers")
    doctor = await svc.get_by_user_id(user.id)
    if not doctor:
        raise HTTPException(404, "Doctor profile not found")
    return doctor.id


@router.get("/", response_model=list[OfferRead])
async def list_my_offers(user: CurrentUser, svc: OfferSvc, doctor_svc: DoctorSvc):
    doctor_id = await _get_doctor_id(user, doctor_svc)
    offers = await svc.get_by_doctor(doctor_id)
    return [_offer_to_read(o) for o in offers]


@router.get("/pending", response_model=list[OfferRead])
async def list_pending_offers(user: CurrentUser, svc: OfferSvc, doctor_svc: DoctorSvc):
    doctor_id = await _get_doctor_id(user, doctor_svc)
    offers = await svc.get_pending_by_doctor(doctor_id)
    return [_offer_to_read(o) for o in offers]


@router.post("/{offer_id}/accept", response_model=OfferRead)
async def accept_offer(offer_id: uuid.UUID, user: CurrentUser, svc: OfferSvc, doctor_svc: DoctorSvc):
    await _get_doctor_id(user, doctor_svc)
    try:
        offer = await svc.accept(offer_id)
        if not offer:
            raise HTTPException(404, "Offer not found")
        return _offer_to_read(offer)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{offer_id}/reject", response_model=OfferRead)
async def reject_offer(
    offer_id: uuid.UUID,
    user: CurrentUser,
    svc: OfferSvc,
    doctor_svc: DoctorSvc,
    data: OfferRespond | None = None,
):
    await _get_doctor_id(user, doctor_svc)
    try:
        offer = await svc.reject(offer_id, data.response_note if data else None)
        if not offer:
            raise HTTPException(404, "Offer not found")
        return _offer_to_read(offer)
    except ValueError as e:
        raise HTTPException(400, str(e))
