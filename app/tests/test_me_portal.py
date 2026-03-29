"""Tests for the doctor self-service portal (/me/) endpoints."""
import uuid
from datetime import date, time

import pytest
from httpx import AsyncClient

from app.utils.enums import AvailabilityType, UnavailabilityReason


pytestmark = pytest.mark.asyncio


# --- Availability ---


async def test_medico_can_create_and_get_availability(
    client: AsyncClient, medico_headers, sample_doctor_with_user,
):
    # Create availability
    resp = await client.post(
        "/api/v1/me/availability",
        json={
            "date": "2026-04-15",
            "start_time": "08:00:00",
            "end_time": "20:00:00",
            "availability_type": "available",
        },
        headers=medico_headers,
    )
    assert resp.status_code == 201
    avail_id = resp.json()["id"]

    # Get availability
    resp = await client.get(
        "/api/v1/me/availability",
        params={"start": "2026-04-01", "end": "2026-04-30"},
        headers=medico_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(a["id"] == avail_id for a in data)


async def test_medico_can_delete_own_availability(
    client: AsyncClient, medico_headers, sample_doctor_with_user,
):
    # Create
    resp = await client.post(
        "/api/v1/me/availability",
        json={
            "date": "2026-04-16",
            "start_time": "08:00:00",
            "end_time": "20:00:00",
        },
        headers=medico_headers,
    )
    assert resp.status_code == 201
    avail_id = resp.json()["id"]

    # Delete
    resp = await client.delete(f"/api/v1/me/availability/{avail_id}", headers=medico_headers)
    assert resp.status_code == 204


async def test_medico_cannot_delete_other_doctors_availability(
    client: AsyncClient, session, medico_headers, sample_doctor_with_user,
):
    """A doctor should NOT be able to delete another doctor's availability."""
    from app.core.security import hash_password
    from app.models.availability import DoctorAvailability
    from app.models.doctor import Doctor

    # Create a separate doctor (not linked to medico_user)
    other_doctor = Doctor(
        fiscal_code="BNCLRA85B02F205X",
        first_name="Laura",
        last_name="Bianchi",
        email="laura@example.com",
        password_hash=hash_password("password123"),
        lat=42.0,
        lon=12.5,
        max_distance_km=50.0,
        is_active=True,
    )
    session.add(other_doctor)
    await session.flush()

    # Create availability for the other doctor
    other_avail = DoctorAvailability(
        doctor_id=other_doctor.id,
        date=date(2026, 4, 20),
        start_time=time(8, 0),
        end_time=time(20, 0),
        availability_type=AvailabilityType.AVAILABLE,
    )
    session.add(other_avail)
    await session.flush()

    # Try to delete it as medico_user
    resp = await client.delete(
        f"/api/v1/me/availability/{other_avail.id}", headers=medico_headers,
    )
    assert resp.status_code == 404


async def test_medico_can_create_and_delete_unavailability(
    client: AsyncClient, medico_headers, sample_doctor_with_user,
):
    # Create
    resp = await client.post(
        "/api/v1/me/unavailability",
        json={
            "start_date": "2026-05-01",
            "end_date": "2026-05-07",
            "reason": "vacation",
        },
        headers=medico_headers,
    )
    assert resp.status_code == 201
    unav_id = resp.json()["id"]

    # Get
    resp = await client.get("/api/v1/me/unavailability", headers=medico_headers)
    assert resp.status_code == 200
    assert any(u["id"] == unav_id for u in resp.json())

    # Delete
    resp = await client.delete(f"/api/v1/me/unavailability/{unav_id}", headers=medico_headers)
    assert resp.status_code == 204


# --- Certifications ---


async def test_medico_can_manage_certifications(
    client: AsyncClient, medico_headers, sample_doctor_with_user, seed_lookups,
):
    # Get existing certifications (BLS added by fixture)
    resp = await client.get("/api/v1/me/certifications", headers=medico_headers)
    assert resp.status_code == 200
    certs = resp.json()
    assert len(certs) >= 1

    # Add ACLS certification
    acls_id = seed_lookups["cert_acls"].id
    resp = await client.post(
        "/api/v1/me/certifications",
        json={
            "certification_type_id": acls_id,
            "obtained_date": "2026-01-01",
            "expiry_date": "2028-01-01",
        },
        headers=medico_headers,
    )
    assert resp.status_code == 201

    # Delete ACLS
    resp = await client.delete(f"/api/v1/me/certifications/{acls_id}", headers=medico_headers)
    assert resp.status_code == 204


# --- Languages ---


async def test_medico_can_manage_languages(
    client: AsyncClient, medico_headers, sample_doctor_with_user, seed_lookups,
):
    # Get existing languages (IT added by fixture)
    resp = await client.get("/api/v1/me/languages", headers=medico_headers)
    assert resp.status_code == 200
    langs = resp.json()
    assert len(langs) >= 1

    # Add English
    en_id = seed_lookups["lang_en"].id
    resp = await client.post(
        "/api/v1/me/languages",
        json={"language_id": en_id, "proficiency_level": 4},
        headers=medico_headers,
    )
    assert resp.status_code == 201

    # Delete English
    resp = await client.delete(f"/api/v1/me/languages/{en_id}", headers=medico_headers)
    assert resp.status_code == 204


# --- Preferences ---


async def test_preferences_create_and_update_idempotent(
    client: AsyncClient, medico_headers, sample_doctor_with_user,
):
    # GET should return null initially
    resp = await client.get("/api/v1/me/preferences", headers=medico_headers)
    assert resp.status_code == 200
    assert resp.json() is None

    # PUT creates preferences
    pref_data = {
        "prefers_day": True,
        "prefers_night": False,
        "prefers_weekends": True,
        "avoids_weekends": False,
        "min_pay_per_shift": 300.0,
    }
    resp = await client.put("/api/v1/me/preferences", json=pref_data, headers=medico_headers)
    assert resp.status_code == 200
    result = resp.json()
    assert result["prefers_day"] is True
    assert result["prefers_weekends"] is True
    assert result["min_pay_per_shift"] == 300.0

    # PUT again updates (idempotent)
    pref_data["min_pay_per_shift"] = 400.0
    resp = await client.put("/api/v1/me/preferences", json=pref_data, headers=medico_headers)
    assert resp.status_code == 200
    assert resp.json()["min_pay_per_shift"] == 400.0

    # GET confirms the update
    resp = await client.get("/api/v1/me/preferences", headers=medico_headers)
    assert resp.status_code == 200
    assert resp.json()["min_pay_per_shift"] == 400.0


# --- Access control ---


async def test_admin_gets_403_on_me_endpoints(
    client: AsyncClient, admin_headers, admin_user,
):
    endpoints = [
        ("GET", "/api/v1/me/availability?start=2026-04-01&end=2026-04-30"),
        ("GET", "/api/v1/me/certifications"),
        ("GET", "/api/v1/me/languages"),
        ("GET", "/api/v1/me/preferences"),
        ("GET", "/api/v1/me/profile"),
    ]
    for method, url in endpoints:
        resp = await client.request(method, url, headers=admin_headers)
        assert resp.status_code == 403, f"Expected 403 for {method} {url}, got {resp.status_code}"


async def test_unauthenticated_gets_401_on_me_endpoints(client: AsyncClient):
    endpoints = [
        ("GET", "/api/v1/me/availability?start=2026-04-01&end=2026-04-30"),
        ("GET", "/api/v1/me/certifications"),
        ("GET", "/api/v1/me/languages"),
        ("GET", "/api/v1/me/preferences"),
        ("GET", "/api/v1/me/profile"),
    ]
    for method, url in endpoints:
        resp = await client.request(method, url)
        assert resp.status_code == 401, f"Expected 401 for {method} {url}, got {resp.status_code}"
