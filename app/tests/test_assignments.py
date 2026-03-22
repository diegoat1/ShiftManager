import pytest


@pytest.mark.asyncio
async def test_check_eligibility_endpoint(client, admin_headers):
    # Setup: create doctor, institution, site, shift, availability, lookups
    ct = await client.post("/api/v1/lookups/certification-types", json={"name": "BLS", "validity_months": 24})
    ct_id = ct.json()["id"]
    lang = await client.post("/api/v1/lookups/languages", json={"code": "it", "name": "Italiano"})
    lang_id = lang.json()["id"]

    doc = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "ASN001", "first_name": "Test", "last_name": "Doc",
        "email": "asn1@test.com", "password": "pass", "lat": 41.9, "lon": 12.5,
    }, headers=admin_headers)
    doc_id = doc.json()["id"]

    await client.post(f"/api/v1/doctors/{doc_id}/certifications", json={
        "certification_type_id": ct_id, "obtained_date": "2025-01-01", "expiry_date": "2027-01-01",
    }, headers=admin_headers)
    await client.post(f"/api/v1/doctors/{doc_id}/languages", json={
        "language_id": lang_id, "proficiency_level": 5,
    }, headers=admin_headers)

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale", "tax_code": "ASN001",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS", "lat": 41.88, "lon": 12.47,
    }, headers=admin_headers)
    site_id = site.json()["id"]

    shift = await client.post("/api/v1/shifts/", json={
        "site_id": site_id,
        "date": "2026-04-01",
        "start_datetime": "2026-04-01T08:00:00",
        "end_datetime": "2026-04-01T20:00:00",
    }, headers=admin_headers)
    shift_id = shift.json()["id"]

    # Add requirements to shift
    await client.post(f"/api/v1/shifts/{shift_id}/requirements", json={
        "certification_type_id": ct_id, "is_mandatory": True,
    }, headers=admin_headers)
    await client.post(f"/api/v1/shifts/{shift_id}/language-requirements", json={
        "language_id": lang_id, "min_proficiency": 3,
    }, headers=admin_headers)

    # Set availability
    await client.post(f"/api/v1/doctors/{doc_id}/availability", json={
        "date": "2026-04-01", "start_time": "00:00:00", "end_time": "23:59:00",
    }, headers=admin_headers)

    # Check eligibility
    resp = await client.get(f"/api/v1/assignments/check/{doc_id}/{shift_id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_eligible"] is True


@pytest.mark.asyncio
async def test_assign_and_unassign(client, admin_headers):
    # Setup minimal
    doc = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "ASN002", "first_name": "T", "last_name": "D",
        "email": "asn2@test.com", "password": "pass", "lat": 41.9, "lon": 12.5,
    }, headers=admin_headers)
    doc_id = doc.json()["id"]

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "ASN002",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS", "lat": 41.9, "lon": 12.5,
    }, headers=admin_headers)
    site_id = site.json()["id"]

    shift = await client.post("/api/v1/shifts/", json={
        "site_id": site_id,
        "date": "2026-04-01",
        "start_datetime": "2026-04-01T08:00:00",
        "end_datetime": "2026-04-01T20:00:00",
    }, headers=admin_headers)
    shift_id = shift.json()["id"]

    await client.post(f"/api/v1/doctors/{doc_id}/availability", json={
        "date": "2026-04-01", "start_time": "00:00:00", "end_time": "23:59:00",
    }, headers=admin_headers)

    # Assign
    resp = await client.post("/api/v1/assignments/", json={
        "shift_id": shift_id, "doctor_id": doc_id,
    }, headers=admin_headers)
    assert resp.status_code == 201
    assignment_id = resp.json()["id"]

    # List shift assignments
    resp = await client.get(f"/api/v1/assignments/shift/{shift_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Unassign
    resp = await client.delete(f"/api/v1/assignments/{assignment_id}", headers=admin_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_assign_ineligible_doctor(client, admin_headers):
    doc = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "ASN003", "first_name": "T", "last_name": "D",
        "email": "asn3@test.com", "password": "pass",
    }, headers=admin_headers)
    doc_id = doc.json()["id"]

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "ASN003",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={"name": "PS"}, headers=admin_headers)
    site_id = site.json()["id"]

    shift = await client.post("/api/v1/shifts/", json={
        "site_id": site_id,
        "date": "2026-04-01",
        "start_datetime": "2026-04-01T08:00:00",
        "end_datetime": "2026-04-01T20:00:00",
    }, headers=admin_headers)
    shift_id = shift.json()["id"]

    # No availability set — should fail
    resp = await client.post("/api/v1/assignments/", json={
        "shift_id": shift_id, "doctor_id": doc_id,
    }, headers=admin_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_eligible_doctors(client, admin_headers):
    inst = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "ASN004",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS", "lat": 41.9, "lon": 12.5,
    }, headers=admin_headers)
    site_id = site.json()["id"]

    shift = await client.post("/api/v1/shifts/", json={
        "site_id": site_id,
        "date": "2026-04-01",
        "start_datetime": "2026-04-01T08:00:00",
        "end_datetime": "2026-04-01T20:00:00",
    }, headers=admin_headers)
    shift_id = shift.json()["id"]

    resp = await client.get(f"/api/v1/assignments/eligible/{shift_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
