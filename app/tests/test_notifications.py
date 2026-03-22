import pytest

from app.models.notification import Notification


@pytest.mark.asyncio
async def test_list_notifications(client, admin_headers, admin_user, session):
    n = Notification(
        user_id=admin_user.id,
        type="test",
        title="Test notification",
        body="This is a test",
    )
    session.add(n)
    await session.flush()

    resp = await client.get("/api/v1/me/notifications/", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test notification"


@pytest.mark.asyncio
async def test_unread_count(client, admin_headers, admin_user, session):
    for i in range(3):
        session.add(Notification(user_id=admin_user.id, type="test", title=f"N{i}"))
    await session.flush()

    resp = await client.get("/api/v1/me/notifications/unread-count", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["count"] == 3


@pytest.mark.asyncio
async def test_mark_read(client, admin_headers, admin_user, session):
    n = Notification(user_id=admin_user.id, type="test", title="Read me")
    session.add(n)
    await session.flush()

    resp = await client.patch(f"/api/v1/me/notifications/{n.id}/read", headers=admin_headers)
    assert resp.status_code == 200

    resp = await client.get("/api/v1/me/notifications/unread-count", headers=admin_headers)
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_mark_all_read(client, admin_headers, admin_user, session):
    for i in range(5):
        session.add(Notification(user_id=admin_user.id, type="test", title=f"N{i}"))
    await session.flush()

    resp = await client.post("/api/v1/me/notifications/read-all", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["marked"] == 5

    resp = await client.get("/api/v1/me/notifications/unread-count", headers=admin_headers)
    assert resp.json()["count"] == 0
