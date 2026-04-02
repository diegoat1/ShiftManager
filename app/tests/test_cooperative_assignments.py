from datetime import date

import pytest


@pytest.mark.asyncio
async def test_create_site_assignment(client, admin_headers):
    """POST /cooperatives/{coop_id}/sites creates an assignment."""
    coop = await client.post("/api/v1/cooperatives/", json={"name": "CoopA"}, headers=admin_headers)
    coop_id = coop.json()["id"]

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "CSA001",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS",
    }, headers=admin_headers)
    site_id = site.json()["id"]

    resp = await client.post(f"/api/v1/cooperatives/{coop_id}/sites", json={
        "site_id": site_id,
        "start_date": "2026-01-01",
    }, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["cooperative_id"] == coop_id
    assert data["site_id"] == site_id
    assert data["start_date"] == "2026-01-01"
    assert data["end_date"] is None


@pytest.mark.asyncio
async def test_reject_overlapping_assignment(client, admin_headers):
    """Overlapping assignments for the same site are rejected."""
    coop = await client.post("/api/v1/cooperatives/", json={"name": "CoopB"}, headers=admin_headers)
    coop_id = coop.json()["id"]
    coop2 = await client.post("/api/v1/cooperatives/", json={"name": "CoopC"}, headers=admin_headers)
    coop2_id = coop2.json()["id"]

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "CSA002",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS",
    }, headers=admin_headers)
    site_id = site.json()["id"]

    # First assignment: ongoing
    resp1 = await client.post(f"/api/v1/cooperatives/{coop_id}/sites", json={
        "site_id": site_id,
        "start_date": "2026-01-01",
    }, headers=admin_headers)
    assert resp1.status_code == 201

    # Second assignment on same site: should fail (overlap)
    resp2 = await client.post(f"/api/v1/cooperatives/{coop2_id}/sites", json={
        "site_id": site_id,
        "start_date": "2026-06-01",
    }, headers=admin_headers)
    assert resp2.status_code == 400
    assert "Overlapping" in resp2.json()["detail"]


@pytest.mark.asyncio
async def test_deactivate_assignment_then_new(client, admin_headers):
    """After ending an assignment, a new one can be created."""
    coop = await client.post("/api/v1/cooperatives/", json={"name": "CoopD"}, headers=admin_headers)
    coop_id = coop.json()["id"]
    coop2 = await client.post("/api/v1/cooperatives/", json={"name": "CoopE"}, headers=admin_headers)
    coop2_id = coop2.json()["id"]

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "CSA003",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS",
    }, headers=admin_headers)
    site_id = site.json()["id"]

    # Create ongoing assignment
    resp1 = await client.post(f"/api/v1/cooperatives/{coop_id}/sites", json={
        "site_id": site_id,
        "start_date": "2026-01-01",
    }, headers=admin_headers)
    assert resp1.status_code == 201
    assignment_id = resp1.json()["id"]

    # End it by setting end_date
    resp_end = await client.patch(f"/api/v1/cooperatives/{coop_id}/sites/{assignment_id}", json={
        "end_date": "2026-05-31",
    }, headers=admin_headers)
    assert resp_end.status_code == 200
    assert resp_end.json()["end_date"] == "2026-05-31"

    # Now a new assignment starting after can be created
    resp2 = await client.post(f"/api/v1/cooperatives/{coop2_id}/sites", json={
        "site_id": site_id,
        "start_date": "2026-06-01",
    }, headers=admin_headers)
    assert resp2.status_code == 201


@pytest.mark.asyncio
async def test_get_active_cooperative_for_site(client, admin_headers):
    """GET /institutions/sites/{site_id}/cooperative returns active cooperative."""
    coop = await client.post("/api/v1/cooperatives/", json={"name": "CoopF"}, headers=admin_headers)
    coop_id = coop.json()["id"]

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "CSA004",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS",
    }, headers=admin_headers)
    site_id = site.json()["id"]

    # No assignment yet
    resp = await client.get(f"/api/v1/institutions/sites/{site_id}/cooperative")
    assert resp.status_code == 200
    assert resp.json() is None

    # Create assignment
    await client.post(f"/api/v1/cooperatives/{coop_id}/sites", json={
        "site_id": site_id,
        "start_date": "2026-01-01",
    }, headers=admin_headers)

    # Now should return it
    resp = await client.get(f"/api/v1/institutions/sites/{site_id}/cooperative")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cooperative_id"] == coop_id


@pytest.mark.asyncio
async def test_end_date_before_start_date_rejected(client, admin_headers):
    """end_date < start_date is rejected at schema validation."""
    coop = await client.post("/api/v1/cooperatives/", json={"name": "CoopG"}, headers=admin_headers)
    coop_id = coop.json()["id"]

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "CSA005",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS",
    }, headers=admin_headers)
    site_id = site.json()["id"]

    resp = await client.post(f"/api/v1/cooperatives/{coop_id}/sites", json={
        "site_id": site_id,
        "start_date": "2026-06-01",
        "end_date": "2026-01-01",
    }, headers=admin_headers)
    assert resp.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_institution_create_no_cooperative_id(client, admin_headers):
    """POST /institutions/ no longer accepts cooperative_id."""
    resp = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "CSA006",
    }, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert "cooperative_id" not in data


@pytest.mark.asyncio
async def test_patch_assignment_wrong_cooperative(client, admin_headers):
    """PATCH with wrong coop_id returns 404."""
    coop = await client.post("/api/v1/cooperatives/", json={"name": "CoopH"}, headers=admin_headers)
    coop_id = coop.json()["id"]
    coop2 = await client.post("/api/v1/cooperatives/", json={"name": "CoopI"}, headers=admin_headers)
    coop2_id = coop2.json()["id"]

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "CSA007",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS",
    }, headers=admin_headers)
    site_id = site.json()["id"]

    resp = await client.post(f"/api/v1/cooperatives/{coop_id}/sites", json={
        "site_id": site_id,
        "start_date": "2026-01-01",
    }, headers=admin_headers)
    assignment_id = resp.json()["id"]

    # Try to patch via wrong cooperative
    resp = await client.patch(f"/api/v1/cooperatives/{coop2_id}/sites/{assignment_id}", json={
        "end_date": "2026-12-31",
    }, headers=admin_headers)
    assert resp.status_code == 404
