import pytest


@pytest.mark.asyncio
async def test_get_kpis(client, admin_headers):
    resp = await client.get("/api/v1/admin/analytics/kpis", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_shifts" in data
    assert "coverage_percent" in data
    assert "active_doctors" in data


@pytest.mark.asyncio
async def test_get_kpis_by_month(client, admin_headers):
    resp = await client.get("/api/v1/admin/analytics/kpis/by-month", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 12  # 12 months


@pytest.mark.asyncio
async def test_kpis_require_admin(client, medico_headers):
    resp = await client.get("/api/v1/admin/analytics/kpis", headers=medico_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_audit_log(client, admin_headers):
    resp = await client.get("/api/v1/admin/audit-log/", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
