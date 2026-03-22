from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, get_auth_service
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest
from app.schemas.user import UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

AuthSvc = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/login", response_model=LoginResponse)
async def login(data: LoginRequest, svc: AuthSvc):
    try:
        return await svc.login(data)
    except ValueError as e:
        raise HTTPException(401, str(e))


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(data: RegisterRequest, svc: AuthSvc):
    try:
        return await svc.register(data)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/me", response_model=UserRead)
async def get_me(user: CurrentUser):
    return user
