import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession):
        super().__init__(Notification, session)

    async def get_by_user(self, user_id: uuid.UUID, skip: int = 0, limit: int = 50) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.sent_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def unread_count(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id, Notification.status == "unread")
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        from datetime import datetime
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id, Notification.status == "unread")
        )
        result = await self.session.execute(stmt)
        notifications = result.scalars().all()
        now = datetime.utcnow()
        for n in notifications:
            n.status = "read"
            n.read_at = now
        await self.session.flush()
        return len(notifications)
