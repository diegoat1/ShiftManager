import pytest


@pytest.mark.asyncio
async def test_create_institution(client, admin_headers):
    resp = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale Test",
        "tax_code": "12345678901",
        "city": "Roma",
        "province": "RM",
    }, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Ospedale Test"


@pytest.mark.asyncio
async def test_create_site(client, admin_headers):
    inst = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale", "tax_code": "111",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]

    resp = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "Pronto Soccorso",
        "lat": 41.88,
        "lon": 12.47,
    }, headers=admin_headers)
    assert resp.status_code == 201
    assert resp.json()["name"] == "Pronto Soccorso"


@pytest.mark.asyncio
async def test_list_sites(client, admin_headers):
    inst = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale", "tax_code": "222",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    await client.post(f"/api/v1/institutions/{inst_id}/sites", json={"name": "Site A"}, headers=admin_headers)
    await client.post(f"/api/v1/institutions/{inst_id}/sites", json={"name": "Site B"}, headers=admin_headers)

    resp = await client.get(f"/api/v1/institutions/{inst_id}/sites", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_add_requirement(client, admin_headers):
    ct = await client.post("/api/v1/lookups/certification-types", json={"name": "BLS"})
    ct_id = ct.json()["id"]

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale", "tax_code": "333",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]

    resp = await client.post(f"/api/v1/institutions/{inst_id}/requirements", json={
        "certification_type_id": ct_id,
        "is_mandatory": True,
    }, headers=admin_headers)
    assert resp.status_code == 201

    reqs = await client.get(f"/api/v1/institutions/{inst_id}/requirements", headers=admin_headers)
    assert len(reqs.json()) == 1
