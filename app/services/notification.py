import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.notification import NotificationRepository


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = NotificationRepository(session)

    async def create(
        self,
        user_id: uuid.UUID,
        type: str,
        title: str,
        body: str | None = None,
        related_entity_type: str | None = None,
        related_entity_id: str | None = None,
    ) -> Notification:
        notif = await self.repo.create(
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )

        return notif

    async def get_by_user(self, user_id: uuid.UUID, skip: int = 0, limit: int = 50):
        return await self.repo.get_by_user(user_id, skip, limit)

    async def unread_count(self, user_id: uuid.UUID) -> int:
        return await self.repo.unread_count(user_id)

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        notif = await self.repo.get_by_id(notification_id)
        if not notif or notif.user_id != user_id:
            return False
        notif.status = "read"
        notif.read_at = datetime.utcnow()
        await self.session.flush()

        return True

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        count = await self.repo.mark_all_read(user_id)

        return count
