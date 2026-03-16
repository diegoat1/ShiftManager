import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_assignment_service
from app.schemas.assignment import AssignmentCreate, AssignmentRead, EligibilityResult, ScoredEligibleDoctorRead
from app.services.assignment import AssignmentService

router = APIRouter(prefix="/assignments", tags=["assignments"])

AssignSvc = Annotated[AssignmentService, Depends(get_assignment_service)]


@router.post("/", response_model=AssignmentRead, status_code=201)
async def assign_doctor(data: AssignmentCreate, svc: AssignSvc):
    assignment, result = await svc.assign(data)
    if not assignment:
        raise HTTPException(400, detail={"message": "Not eligible", "eligibility": result.model_dump()})
    return assignment


@router.delete("/{assignment_id}", status_code=204)
async def unassign_doctor(assignment_id: uuid.UUID, svc: AssignSvc):
    if not await svc.unassign(assignment_id):
        raise HTTPException(404, "Assignment not found")


@router.get("/check/{doctor_id}/{shift_id}", response_model=EligibilityResult)
async def check_eligibility(doctor_id: uuid.UUID, shift_id: uuid.UUID, svc: AssignSvc):
    return await svc.check_eligibility(doctor_id, shift_id)


@router.get("/eligible/{shift_id}", response_model=list[ScoredEligibleDoctorRead])
async def get_eligible_doctors(shift_id: uuid.UUID, svc: AssignSvc):
    return await svc.get_eligible_doctors(shift_id)


@router.get("/shift/{shift_id}", response_model=list[AssignmentRead])
async def list_shift_assignments(shift_id: uuid.UUID, svc: AssignSvc):
    return await svc.get_by_shift(shift_id)


@router.get("/doctor/{doctor_id}", response_model=list[AssignmentRead])
async def list_doctor_assignments(doctor_id: uuid.UUID, svc: AssignSvc):
    return await svc.get_by_doctor(doctor_id)
