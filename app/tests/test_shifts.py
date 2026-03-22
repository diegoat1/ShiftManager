import pytest


@pytest.mark.asyncio
async def test_create_shift(client, admin_headers):
    inst = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale", "tax_code": "S001",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS", "lat": 41.88, "lon": 12.47,
    }, headers=admin_headers)
    site_id = site.json()["id"]

    resp = await client.post("/api/v1/shifts/", json={
        "site_id": site_id,
        "date": "2026-04-01",
        "start_datetime": "2026-04-01T08:00:00",
        "end_datetime": "2026-04-01T20:00:00",
        "required_doctors": 2,
        "base_pay": 600.0,
    }, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["required_doctors"] == 2
    assert data["base_pay"] == 600.0


@pytest.mark.asyncio
async def test_create_template_and_generate(client, admin_headers):
    inst = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale", "tax_code": "S002",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS", "lat": 41.88, "lon": 12.47,
    }, headers=admin_headers)
    site_id = site.json()["id"]

    tmpl = await client.post("/api/v1/shifts/templates", json={
        "site_id": site_id,
        "name": "Morning",
        "start_time": "08:00:00",
        "end_time": "14:00:00",
        "required_doctors": 1,
        "base_pay": 300.0,
    }, headers=admin_headers)
    assert tmpl.status_code == 201
    tmpl_id = tmpl.json()["id"]

    resp = await client.post("/api/v1/shifts/generate", json={
        "site_id": site_id,
        "template_ids": [tmpl_id],
        "start_date": "2026-04-01",
        "end_date": "2026-04-03",
    }, headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3  # 3 days


@pytest.mark.asyncio
async def test_shift_inherits_institution_requirements(client, admin_headers):
    # Create lookup
    ct = await client.post("/api/v1/lookups/certification-types", json={"name": "BLS"})
    ct_id = ct.json()["id"]

    # Create institution with requirement
    inst = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale", "tax_code": "S003",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS",
    }, headers=admin_headers)
    site_id = site.json()["id"]
    await client.post(f"/api/v1/institutions/{inst_id}/requirements", json={
        "certification_type_id": ct_id, "is_mandatory": True,
    }, headers=admin_headers)

    # Create shift — should inherit requirement
    shift = await client.post("/api/v1/shifts/", json={
        "site_id": site_id,
        "date": "2026-04-01",
        "start_datetime": "2026-04-01T08:00:00",
        "end_datetime": "2026-04-01T20:00:00",
    }, headers=admin_headers)
    assert shift.status_code == 201
