import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, get_notification_service
from app.schemas.notification import NotificationRead, UnreadCountResponse
from app.services.notification import NotificationService

router = APIRouter(prefix="/me/notifications", tags=["notifications"])

NotifSvc = Annotated[NotificationService, Depends(get_notification_service)]


@router.get("/", response_model=list[NotificationRead])
async def list_notifications(user: CurrentUser, svc: NotifSvc, skip: int = 0, limit: int = 50):
    return await svc.get_by_user(user.id, skip, limit)


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(user: CurrentUser, svc: NotifSvc):
    count = await svc.unread_count(user.id)
    return UnreadCountResponse(count=count)


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: uuid.UUID, user: CurrentUser, svc: NotifSvc):
    if not await svc.mark_read(notification_id, user.id):
        raise HTTPException(404, "Notification not found")
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(user: CurrentUser, svc: NotifSvc):
    count = await svc.mark_all_read(user.id)
    return {"marked": count}
