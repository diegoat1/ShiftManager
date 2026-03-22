import pytest
from datetime import datetime

from app.models.offer import ShiftOffer
from app.utils.enums import OfferStatus


@pytest.mark.asyncio
async def test_send_offer(client, admin_headers, sample_shift, sample_doctor, sample_availability, session):
    resp = await client.post(
        f"/api/v1/shifts/{sample_shift.id}/offers/send",
        headers=admin_headers,
        json={"doctor_id": str(sample_doctor.id), "expires_in_hours": 12},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "proposed"
    assert data["doctor_id"] == str(sample_doctor.id)


@pytest.mark.asyncio
async def test_send_duplicate_offer(client, admin_headers, sample_shift, sample_doctor, sample_availability, session):
    await client.post(
        f"/api/v1/shifts/{sample_shift.id}/offers/send",
        headers=admin_headers,
        json={"doctor_id": str(sample_doctor.id)},
    )
    resp = await client.post(
        f"/api/v1/shifts/{sample_shift.id}/offers/send",
        headers=admin_headers,
        json={"doctor_id": str(sample_doctor.id)},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_shift_offers(client, admin_headers, sample_shift, sample_doctor, sample_availability, session):
    await client.post(
        f"/api/v1/shifts/{sample_shift.id}/offers/send",
        headers=admin_headers,
        json={"doctor_id": str(sample_doctor.id)},
    )
    resp = await client.get(f"/api/v1/shifts/{sample_shift.id}/offers/", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_cancel_offer(client, admin_headers, sample_shift, sample_doctor, sample_availability, session):
    create_resp = await client.post(
        f"/api/v1/shifts/{sample_shift.id}/offers/send",
        headers=admin_headers,
        json={"doctor_id": str(sample_doctor.id)},
    )
    offer_id = create_resp.json()["id"]
    resp = await client.post(
        f"/api/v1/shifts/{sample_shift.id}/offers/{offer_id}/cancel",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_doctor_offers(client, medico_headers, sample_doctor_with_user, sample_shift, session):
    # Create offer manually
    offer = ShiftOffer(
        shift_id=sample_shift.id,
        doctor_id=sample_doctor_with_user.id,
        status=OfferStatus.PROPOSED,
    )
    session.add(offer)
    await session.flush()

    resp = await client.get("/api/v1/me/offers/", headers=medico_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_doctor_pending_offers(client, medico_headers, sample_doctor_with_user, sample_shift, session):
    offer = ShiftOffer(
        shift_id=sample_shift.id,
        doctor_id=sample_doctor_with_user.id,
        status=OfferStatus.PROPOSED,
    )
    session.add(offer)
    await session.flush()

    resp = await client.get("/api/v1/me/offers/pending", headers=medico_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
