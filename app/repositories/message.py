import uuid
from typing import Sequence

from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.doctor import Doctor
from app.models.message import Message
from app.utils.dates import utcnow_naive
from app.models.user import User


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, **kwargs) -> Message:
        msg = Message(**kwargs)
        self.session.add(msg)
        await self.session.flush()
        return msg

    async def get_messages_between(
        self,
        user_id: uuid.UUID,
        other_user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[Message]:
        """Get messages between two users, ascending order (natural chat order)."""
        stmt = (
            select(Message)
            .where(
                or_(
                    and_(Message.sender_id == user_id, Message.recipient_id == other_user_id),
                    and_(Message.sender_id == other_user_id, Message.recipient_id == user_id),
                )
            )
            .order_by(Message.sent_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def unread_count(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Message).where(
                Message.recipient_id == user_id,
                Message.read_at == None,
            )
        )
        return result.scalar_one()

    async def mark_conversation_read(
        self, user_id: uuid.UUID, other_user_id: uuid.UUID
    ) -> int:
        """Mark all received messages from other_user as read."""
        result = await self.session.execute(
            update(Message)
            .where(
                Message.sender_id == other_user_id,
                Message.recipient_id == user_id,
                Message.read_at == None,
            )
            .values(read_at=utcnow_naive())
        )
        return result.rowcount

    async def get_conversations(self, user_id: uuid.UUID) -> list[dict]:
        """Get conversation summaries grouped by partner user."""
        # Get distinct partner user IDs
        partner_id_expr = case(
            (Message.sender_id == user_id, Message.recipient_id),
            else_=Message.sender_id,
        )

        # Subquery: for each partner, get latest message time
        partner_sub = (
            select(
                partner_id_expr.label("partner_id"),
                func.max(Message.sent_at).label("last_at"),
            )
            .where(or_(Message.sender_id == user_id, Message.recipient_id == user_id))
            .group_by(partner_id_expr)
            .subquery()
        )

        # Join with User + Doctor for name resolution
        stmt = (
            select(
                partner_sub.c.partner_id,
                partner_sub.c.last_at,
                User.email,
                User.role,
                Doctor.first_name,
                Doctor.last_name,
            )
            .join(User, User.id == partner_sub.c.partner_id)
            .outerjoin(Doctor, Doctor.user_id == partner_sub.c.partner_id)
            .order_by(partner_sub.c.last_at.desc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        conversations = []
        for row in rows:
            partner_id = row.partner_id
            # Resolve name: doctor name if available, else email
            if row.first_name and row.last_name:
                name = f"{row.first_name} {row.last_name}"
            else:
                name = row.email

            # Get unread count for this conversation
            unread_result = await self.session.execute(
                select(func.count()).select_from(Message).where(
                    Message.sender_id == partner_id,
                    Message.recipient_id == user_id,
                    Message.read_at == None,
                )
            )
            unread = unread_result.scalar_one()

            # Get last message text
            last_msg_result = await self.session.execute(
                select(Message.body).where(
                    or_(
                        and_(Message.sender_id == user_id, Message.recipient_id == partner_id),
                        and_(Message.sender_id == partner_id, Message.recipient_id == user_id),
                    )
                ).order_by(Message.sent_at.desc()).limit(1)
            )
            last_msg = last_msg_result.scalar_one_or_none() or ""

            role_val = row.role.value if hasattr(row.role, 'value') else str(row.role)

            conversations.append({
                "user_id": partner_id,
                "user_name": name,
                "user_email": row.email,
                "user_role": role_val,
                "last_message": last_msg[:100],
                "last_message_at": row.last_at,
                "unread_count": unread,
            })

        return conversations
