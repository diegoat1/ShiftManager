from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DbSession
from app.models.doctor import CertificationType, Language
from app.models.requirement import CodeLevel
from app.schemas.doctor import CertificationTypeRead, LanguageRead


class CertificationTypeCreate(BaseModel):
    name: str
    description: str | None = None
    validity_months: int | None = None


class CodeLevelRead(BaseModel):
    id: int
    code: str
    description: str | None
    severity_order: int


class CodeLevelCreate(BaseModel):
    code: str
    description: str | None = None
    severity_order: int = 0


class LanguageCreate(BaseModel):
    code: str
    name: str


router = APIRouter(prefix="/lookups", tags=["lookups"])


@router.get("/certification-types", response_model=list[CertificationTypeRead])
async def list_certification_types(session: DbSession):
    result = await session.execute(select(CertificationType))
    return result.scalars().all()


@router.post("/certification-types", response_model=CertificationTypeRead, status_code=201)
async def create_certification_type(data: CertificationTypeCreate, session: DbSession):
    ct = CertificationType(**data.model_dump())
    session.add(ct)
    await session.commit()
    await session.refresh(ct)
    return ct


@router.get("/languages", response_model=list[LanguageRead])
async def list_languages(session: DbSession):
    result = await session.execute(select(Language))
    return result.scalars().all()


@router.post("/languages", response_model=LanguageRead, status_code=201)
async def create_language(data: LanguageCreate, session: DbSession):
    lang = Language(**data.model_dump())
    session.add(lang)
    await session.commit()
    await session.refresh(lang)
    return lang


@router.get("/code-levels", response_model=list[CodeLevelRead])
async def list_code_levels(session: DbSession):
    result = await session.execute(select(CodeLevel))
    return result.scalars().all()


@router.post("/code-levels", response_model=CodeLevelRead, status_code=201)
async def create_code_level(data: CodeLevelCreate, session: DbSession):
    cl = CodeLevel(**data.model_dump())
    session.add(cl)
    await session.commit()
    await session.refresh(cl)
    return cl
