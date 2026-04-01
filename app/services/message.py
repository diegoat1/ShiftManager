import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.doctor import Doctor
from app.models.message import Message
from app.models.user import User
from app.repositories.message import MessageRepository
from app.utils.enums import UserRole

ADMIN_ROLES = {UserRole.SUPERADMIN.value, UserRole.ADMIN.value, UserRole.COORDINATORE.value}


class MessageService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = MessageRepository(session)

    async def send(
        self,
        sender_id: uuid.UUID,
        recipient_id: uuid.UUID,
        body: str,
    ) -> Message:
        body = body.strip()
        if not body:
            raise ValueError("Il messaggio non puo essere vuoto")

        # Validate recipient exists
        recipient = await self.session.get(User, recipient_id)
        if not recipient or not recipient.is_active:
            raise ValueError("Destinatario non trovato")

        # Validate sender
        sender = await self.session.get(User, sender_id)
        if not sender:
            raise ValueError("Mittente non trovato")

        sender_role = sender.role.value if hasattr(sender.role, 'value') else str(sender.role)
        recipient_role = recipient.role.value if hasattr(recipient.role, 'value') else str(recipient.role)

        # Permission check: doctor ↔ admin only
        sender_is_admin = sender_role in ADMIN_ROLES
        recipient_is_admin = recipient_role in ADMIN_ROLES
        sender_is_doctor = sender_role == UserRole.MEDICO.value
        recipient_is_doctor = recipient_role == UserRole.MEDICO.value

        if sender_is_doctor and not recipient_is_admin:
            raise ValueError("I medici possono inviare messaggi solo agli amministratori")
        if sender_is_admin and not recipient_is_doctor:
            raise ValueError("Gli amministratori possono inviare messaggi solo ai medici")

        msg = await self.repo.create(
            sender_id=sender_id,
            recipient_id=recipient_id,
            body=body,
        )

        return msg

    async def get_conversations(self, user_id: uuid.UUID) -> list[dict]:
        return await self.repo.get_conversations(user_id)

    async def get_thread(
        self, user_id: uuid.UUID, other_user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ):
        return await self.repo.get_messages_between(user_id, other_user_id, skip, limit)

    async def mark_conversation_read(self, user_id: uuid.UUID, other_user_id: uuid.UUID) -> int:
        count = await self.repo.mark_conversation_read(user_id, other_user_id)

        return count

    async def unread_count(self, user_id: uuid.UUID) -> int:
        return await self.repo.unread_count(user_id)

    async def get_contactable_users(self, user_id: uuid.UUID, user_role: str) -> list[dict]:
        """Get users this user can message."""
        if user_role in ADMIN_ROLES:
            # Admin can message doctors
            stmt = (
                select(User.id, User.email, User.role, Doctor.first_name, Doctor.last_name)
                .join(Doctor, Doctor.user_id == User.id)
                .where(User.is_active == True, User.id != user_id)
            )
        elif user_role == UserRole.MEDICO.value:
            # Doctor can message admins
            stmt = (
                select(User.id, User.email, User.role)
                .where(
                    User.is_active == True,
                    User.role.in_([UserRole.ADMIN, UserRole.SUPERADMIN, UserRole.COORDINATORE]),
                    User.id != user_id,
                )
            )
        else:
            return []

        result = await self.session.execute(stmt)
        contacts = []
        for row in result.all():
            role_val = row.role.value if hasattr(row.role, 'value') else str(row.role)
            if hasattr(row, 'first_name') and row.first_name:
                name = f"{row.first_name} {row.last_name}"
            else:
                name = row.email
            contacts.append({
                "user_id": row.id,
                "name": name,
                "email": row.email,
                "role": role_val,
            })
        return contacts
