import pytest


@pytest.mark.asyncio
async def test_set_availability(client, admin_headers):
    doc = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "AV001", "first_name": "A", "last_name": "A",
        "email": "av1@test.com", "password": "pass",
    }, headers=admin_headers)
    doc_id = doc.json()["id"]

    resp = await client.post(f"/api/v1/doctors/{doc_id}/availability", json={
        "date": "2026-04-01",
        "start_time": "08:00:00",
        "end_time": "20:00:00",
        "availability_type": "available",
    }, headers=admin_headers)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_get_availability(client, admin_headers):
    doc = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "AV002", "first_name": "B", "last_name": "B",
        "email": "av2@test.com", "password": "pass",
    }, headers=admin_headers)
    doc_id = doc.json()["id"]

    await client.post(f"/api/v1/doctors/{doc_id}/availability", json={
        "date": "2026-04-01", "start_time": "08:00:00", "end_time": "20:00:00",
    }, headers=admin_headers)
    await client.post(f"/api/v1/doctors/{doc_id}/availability", json={
        "date": "2026-04-02", "start_time": "08:00:00", "end_time": "20:00:00",
    }, headers=admin_headers)

    resp = await client.get(
        f"/api/v1/doctors/{doc_id}/availability",
        params={"start": "2026-04-01", "end": "2026-04-02"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_create_unavailability(client, admin_headers):
    doc = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "AV003", "first_name": "C", "last_name": "C",
        "email": "av3@test.com", "password": "pass",
    }, headers=admin_headers)
    doc_id = doc.json()["id"]

    resp = await client.post(f"/api/v1/doctors/{doc_id}/unavailability", json={
        "start_date": "2026-04-10",
        "end_date": "2026-04-15",
        "reason": "vacation",
    }, headers=admin_headers)
    assert resp.status_code == 201
    assert resp.json()["reason"] == "vacation"


@pytest.mark.asyncio
async def test_bulk_availability(client, admin_headers):
    doc = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "AV004", "first_name": "D", "last_name": "D",
        "email": "av4@test.com", "password": "pass",
    }, headers=admin_headers)
    doc_id = doc.json()["id"]

    resp = await client.post(f"/api/v1/doctors/{doc_id}/availability/bulk", json={
        "entries": [
            {"date": "2026-04-01", "start_time": "08:00:00", "end_time": "20:00:00"},
            {"date": "2026-04-02", "start_time": "08:00:00", "end_time": "20:00:00"},
            {"date": "2026-04-03", "start_time": "08:00:00", "end_time": "20:00:00"},
        ]
    }, headers=admin_headers)
    assert resp.status_code == 201
