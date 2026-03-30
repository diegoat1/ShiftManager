import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, get_message_service
from app.schemas.message import (
    ContactRead,
    ConversationSummary,
    MessageCreate,
    MessageRead,
    UnreadMessagesCountResponse,
)
from app.services.message import MessageService

router = APIRouter(prefix="/me/messages", tags=["messages"])

MsgSvc = Annotated[MessageService, Depends(get_message_service)]


# Fixed-path endpoints MUST come before {user_id} path param

@router.get("/unread-count", response_model=UnreadMessagesCountResponse)
async def unread_message_count(user: CurrentUser, svc: MsgSvc):
    count = await svc.unread_count(user.id)
    return UnreadMessagesCountResponse(count=count)


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(user: CurrentUser, svc: MsgSvc):
    return await svc.get_conversations(user.id)


@router.get("/contacts", response_model=list[ContactRead])
async def list_contacts(user: CurrentUser, svc: MsgSvc):
    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
    return await svc.get_contactable_users(user.id, role_val)


# Parameterized endpoints

@router.get("/{user_id}", response_model=list[MessageRead])
async def get_thread(
    user_id: uuid.UUID,
    user: CurrentUser,
    svc: MsgSvc,
    skip: int = 0,
    limit: int = 50,
):
    messages = await svc.get_thread(user.id, user_id, skip, limit)
    return [
        MessageRead(
            id=m.id,
            sender_id=m.sender_id,
            recipient_id=m.recipient_id,
            body=m.body,
            sent_at=m.sent_at,
            read_at=m.read_at,
        )
        for m in messages
    ]


@router.post("/{user_id}", response_model=MessageRead, status_code=201)
async def send_message(
    user_id: uuid.UUID,
    data: MessageCreate,
    user: CurrentUser,
    svc: MsgSvc,
):
    try:
        msg = await svc.send(user.id, user_id, data.body)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return MessageRead(
        id=msg.id,
        sender_id=msg.sender_id,
        recipient_id=msg.recipient_id,
        body=msg.body,
        sent_at=msg.sent_at,
        read_at=msg.read_at,
    )


@router.post("/{user_id}/read")
async def mark_conversation_read(
    user_id: uuid.UUID,
    user: CurrentUser,
    svc: MsgSvc,
):
    count = await svc.mark_conversation_read(user.id, user_id)
    return {"marked": count}
