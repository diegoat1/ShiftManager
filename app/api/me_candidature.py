import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import CurrentDoctor, DbSession, get_assignment_service
from app.api.me_assignments import _to_my_assignment
from app.models.assignment import ASSIGNMENT_SOURCE_SELF_APPLIED
from app.repositories.assignment import AssignmentRepository
from app.schemas.assignment import AvailableShiftRead, CandidatureCreate
from app.services.assignment import AssignmentService
from app.utils.enums import AssignmentStatus

router = APIRouter(prefix="/me", tags=["me-candidature"])

AssignSvc = Annotated[AssignmentService, Depends(get_assignment_service)]


@router.get("/available-shifts", response_model=list[AvailableShiftRead])
async def get_available_shifts(
    doctor: CurrentDoctor,
    svc: AssignSvc,
    start: date = Query(...),
    end: date = Query(...),
    institution_type: str | None = None,
    is_night: bool | None = None,
):
    return await svc.get_available_shifts_for_doctor(
        doctor.id, start, end, institution_type, is_night,
    )


@router.post("/candidature", status_code=201)
async def self_apply(
    data: CandidatureCreate,
    doctor: CurrentDoctor,
    svc: AssignSvc,
):
    assignment, result = await svc.self_apply(doctor.id, data.shift_id)
    if not assignment:
        raise HTTPException(
            400,
            detail=result.reasons[0] if result.reasons else "Non idoneo",
        )
    return _to_my_assignment(assignment)


@router.get("/candidature")
async def list_my_candidatures(
    doctor: CurrentDoctor,
    session: DbSession,
):
    repo = AssignmentRepository(session)
    assignments = await repo.get_by_doctor_with_details(
        doctor_id=doctor.id,
        statuses=[AssignmentStatus.PROPOSED],
    )
    return [
        _to_my_assignment(a)
        for a in assignments
        if getattr(a, 'source', None) == ASSIGNMENT_SOURCE_SELF_APPLIED
    ]


@router.delete("/candidature/{assignment_id}", status_code=204)
async def withdraw_candidature(
    assignment_id: uuid.UUID,
    doctor: CurrentDoctor,
    svc: AssignSvc,
):
    repo = AssignmentRepository(svc.session)
    assignment = await repo.get_by_id(assignment_id)
    if not assignment:
        raise HTTPException(404, "Candidatura non trovata")
    if assignment.doctor_id != doctor.id:
        raise HTTPException(403, "Non autorizzato")
    if assignment.status != AssignmentStatus.PROPOSED:
        raise HTTPException(400, "Solo candidature pendenti possono essere ritirate")
    if getattr(assignment, 'source', None) != ASSIGNMENT_SOURCE_SELF_APPLIED:
        raise HTTPException(400, "Solo auto-candidature possono essere ritirate")
    await svc.unassign(assignment_id)
