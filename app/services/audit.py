import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.audit import AuditLogRepository


class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuditLogRepository(session)

    async def log_action(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: uuid.UUID | None = None,
        old_values: dict | None = None,
        new_values: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        log = await self.repo.create(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=json.dumps(old_values) if old_values else None,
            new_values=json.dumps(new_values) if new_values else None,
            ip_address=ip_address,
        )
        await self.session.flush()
        return log

    async def get_logs(self, skip: int = 0, limit: int = 50, **filters):
        return await self.repo.get_logs(skip=skip, limit=limit, **filters)
