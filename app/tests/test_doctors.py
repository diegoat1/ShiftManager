import pytest


@pytest.mark.asyncio
async def test_create_doctor(client, admin_headers):
    resp = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "BNCLRA90B02F205X",
        "first_name": "Laura",
        "last_name": "Bianchi",
        "email": "laura@example.com",
        "password": "secret123",
        "lat": 41.9,
        "lon": 12.5,
    }, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["fiscal_code"] == "BNCLRA90B02F205X"
    assert data["first_name"] == "Laura"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_doctors(client, admin_headers):
    # Create two doctors
    await client.post("/api/v1/doctors/", json={
        "fiscal_code": "AAA", "first_name": "A", "last_name": "A",
        "email": "a@a.com", "password": "pass",
    }, headers=admin_headers)
    await client.post("/api/v1/doctors/", json={
        "fiscal_code": "BBB", "first_name": "B", "last_name": "B",
        "email": "b@b.com", "password": "pass",
    }, headers=admin_headers)
    resp = await client.get("/api/v1/doctors/", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_get_doctor(client, admin_headers):
    create = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "CCC", "first_name": "C", "last_name": "C",
        "email": "c@c.com", "password": "pass",
    }, headers=admin_headers)
    doc_id = create.json()["id"]
    resp = await client.get(f"/api/v1/doctors/{doc_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == doc_id


@pytest.mark.asyncio
async def test_update_doctor(client, admin_headers):
    create = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "DDD", "first_name": "D", "last_name": "D",
        "email": "d@d.com", "password": "pass",
    }, headers=admin_headers)
    doc_id = create.json()["id"]
    resp = await client.patch(f"/api/v1/doctors/{doc_id}", json={"first_name": "Updated"}, headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["first_name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_doctor(client, admin_headers):
    create = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "EEE", "first_name": "E", "last_name": "E",
        "email": "e@e.com", "password": "pass",
    }, headers=admin_headers)
    doc_id = create.json()["id"]
    resp = await client.delete(f"/api/v1/doctors/{doc_id}", headers=admin_headers)
    assert resp.status_code == 204
    resp = await client.get(f"/api/v1/doctors/{doc_id}", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_add_certification(client, admin_headers):
    # Create lookup
    ct = await client.post("/api/v1/lookups/certification-types", json={"name": "BLS", "validity_months": 24}, headers=admin_headers)
    ct_id = ct.json()["id"]

    doc = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "FFF", "first_name": "F", "last_name": "F",
        "email": "f@f.com", "password": "pass",
    }, headers=admin_headers)
    doc_id = doc.json()["id"]

    resp = await client.post(f"/api/v1/doctors/{doc_id}/certifications", json={
        "certification_type_id": ct_id,
        "obtained_date": "2025-01-01",
    }, headers=admin_headers)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_add_language(client, admin_headers):
    lang = await client.post("/api/v1/lookups/languages", json={"code": "it", "name": "Italiano"}, headers=admin_headers)
    lang_id = lang.json()["id"]

    doc = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "GGG", "first_name": "G", "last_name": "G",
        "email": "g@g.com", "password": "pass",
    }, headers=admin_headers)
    doc_id = doc.json()["id"]

    resp = await client.post(f"/api/v1/doctors/{doc_id}/languages", json={
        "language_id": lang_id,
        "proficiency_level": 5,
    }, headers=admin_headers)
    assert resp.status_code == 201
