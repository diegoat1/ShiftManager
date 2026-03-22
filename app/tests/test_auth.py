import pytest


@pytest.mark.asyncio
async def test_register_medico(client):
    resp = await client.post("/auth/register", json={
        "email": "new@example.com",
        "password": "test123",
        "role": "medico",
        "fiscal_code": "ABCDEF12G34H567I",
        "first_name": "Luca",
        "last_name": "Bianchi",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/auth/register", json={
        "email": "dup@example.com", "password": "test123", "role": "medico",
        "fiscal_code": "AAAAAA00A00A000A", "first_name": "A", "last_name": "B",
    })
    resp = await client.post("/auth/register", json={
        "email": "dup@example.com", "password": "test123", "role": "medico",
        "fiscal_code": "BBBBBB00B00B000B", "first_name": "C", "last_name": "D",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_login(client, admin_user):
    resp = await client.post("/auth/login", json={
        "email": "admin@example.com",
        "password": "admin123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin_user):
    resp = await client.post("/auth/login", json={
        "email": "admin@example.com",
        "password": "wrong",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client, admin_headers, admin_user):
    resp = await client.get("/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin@example.com"
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth(client):
    resp = await client.get("/api/v1/doctors/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_requires_admin(client, medico_headers):
    resp = await client.get("/api/v1/doctors/", headers=medico_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_doctors(client, admin_headers):
    resp = await client.get("/api/v1/doctors/", headers=admin_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_me_profile(client, medico_headers, sample_doctor_with_user):
    resp = await client.get("/api/v1/me/profile", headers=medico_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["first_name"] == "Mario"
    assert data["email"] == "medico@example.com"


@pytest.mark.asyncio
async def test_update_profile(client, medico_headers, sample_doctor_with_user):
    resp = await client.patch("/api/v1/me/profile", headers=medico_headers, json={
        "domicile_city": "Milano",
        "has_own_vehicle": True,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["domicile_city"] == "Milano"
    assert data["has_own_vehicle"] is True
    assert data["profile_completion_percent"] > 0
