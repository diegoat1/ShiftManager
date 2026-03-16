import pytest


@pytest.mark.asyncio
async def test_create_institution(client):
    resp = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale Test",
        "tax_code": "12345678901",
        "city": "Roma",
        "province": "RM",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Ospedale Test"


@pytest.mark.asyncio
async def test_create_site(client):
    inst = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale", "tax_code": "111",
    })
    inst_id = inst.json()["id"]

    resp = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "Pronto Soccorso",
        "lat": 41.88,
        "lon": 12.47,
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "Pronto Soccorso"


@pytest.mark.asyncio
async def test_list_sites(client):
    inst = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale", "tax_code": "222",
    })
    inst_id = inst.json()["id"]
    await client.post(f"/api/v1/institutions/{inst_id}/sites", json={"name": "Site A"})
    await client.post(f"/api/v1/institutions/{inst_id}/sites", json={"name": "Site B"})

    resp = await client.get(f"/api/v1/institutions/{inst_id}/sites")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_add_requirement(client):
    ct = await client.post("/api/v1/lookups/certification-types", json={"name": "BLS"})
    ct_id = ct.json()["id"]

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale", "tax_code": "333",
    })
    inst_id = inst.json()["id"]

    resp = await client.post(f"/api/v1/institutions/{inst_id}/requirements", json={
        "certification_type_id": ct_id,
        "is_mandatory": True,
    })
    assert resp.status_code == 201

    reqs = await client.get(f"/api/v1/institutions/{inst_id}/requirements")
    assert len(reqs.json()) == 1
