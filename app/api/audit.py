from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import RequireAdmin, get_audit_service
from app.schemas.analytics import AuditLogRead
from app.services.audit import AuditService

router = APIRouter(prefix="/admin/audit-log", tags=["audit"])

AuditSvc = Annotated[AuditService, Depends(get_audit_service)]


@router.get("/", response_model=list[AuditLogRead])
async def list_audit_logs(
    admin: RequireAdmin,
    svc: AuditSvc,
    skip: int = 0,
    limit: int = 50,
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
):
    return await svc.get_logs(
        skip=skip,
        limit=limit,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
    )
