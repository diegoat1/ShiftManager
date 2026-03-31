import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.doctor import Doctor, DoctorCertification, DoctorLanguage, DoctorPreference
from app.repositories.base import BaseRepository


class DoctorRepository(BaseRepository[Doctor]):
    def __init__(self, session: AsyncSession):
        super().__init__(Doctor, session)

    async def get_all(self, skip: int = 0, limit: int = 50, search: str | None = None, **filters):  # type: ignore[override]
        stmt = select(Doctor)
        if search:
            q = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Doctor.first_name.ilike(q),
                    Doctor.last_name.ilike(q),
                    Doctor.fiscal_code.ilike(q),
                    Doctor.email.ilike(q),
                )
            )
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self, search: str | None = None, **filters) -> int:  # type: ignore[override]
        stmt = select(func.count()).select_from(Doctor)
        if search:
            q = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Doctor.first_name.ilike(q),
                    Doctor.last_name.ilike(q),
                    Doctor.fiscal_code.ilike(q),
                    Doctor.email.ilike(q),
                )
            )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_by_email(self, email: str) -> Doctor | None:
        result = await self.session.execute(select(Doctor).where(Doctor.email == email))
        return result.scalar_one_or_none()

    async def get_by_fiscal_code(self, fiscal_code: str) -> Doctor | None:
        result = await self.session.execute(select(Doctor).where(Doctor.fiscal_code == fiscal_code))
        return result.scalar_one_or_none()

    async def get_with_relations(self, doctor_id: uuid.UUID) -> Doctor | None:
        stmt = (
            select(Doctor)
            .options(
                selectinload(Doctor.certifications).selectinload(DoctorCertification.certification_type),
                selectinload(Doctor.languages).selectinload(DoctorLanguage.language),
                selectinload(Doctor.preferences),
            )
            .where(Doctor.id == doctor_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_certification(self, **kwargs) -> DoctorCertification:
        cert = DoctorCertification(**kwargs)
        self.session.add(cert)
        await self.session.flush()
        await self.session.refresh(cert)
        return cert

    async def remove_certification(self, doctor_id: uuid.UUID, cert_type_id: int) -> bool:
        stmt = select(DoctorCertification).where(
            DoctorCertification.doctor_id == doctor_id,
            DoctorCertification.certification_type_id == cert_type_id,
        )
        result = await self.session.execute(stmt)
        cert = result.scalar_one_or_none()
        if cert:
            await self.session.delete(cert)
            await self.session.flush()
            return True
        return False

    async def add_language(self, **kwargs) -> DoctorLanguage:
        lang = DoctorLanguage(**kwargs)
        self.session.add(lang)
        await self.session.flush()
        await self.session.refresh(lang)
        return lang

    async def remove_language(self, doctor_id: uuid.UUID, language_id: int) -> bool:
        stmt = select(DoctorLanguage).where(
            DoctorLanguage.doctor_id == doctor_id,
            DoctorLanguage.language_id == language_id,
        )
        result = await self.session.execute(stmt)
        lang = result.scalar_one_or_none()
        if lang:
            await self.session.delete(lang)
            await self.session.flush()
            return True
        return False

    async def get_certifications(self, doctor_id: uuid.UUID) -> list[DoctorCertification]:
        stmt = (
            select(DoctorCertification)
            .options(selectinload(DoctorCertification.certification_type))
            .where(DoctorCertification.doctor_id == doctor_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_languages(self, doctor_id: uuid.UUID) -> list[DoctorLanguage]:
        stmt = (
            select(DoctorLanguage)
            .options(selectinload(DoctorLanguage.language))
            .where(DoctorLanguage.doctor_id == doctor_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_preferences(self, doctor_id: uuid.UUID) -> DoctorPreference | None:
        stmt = select(DoctorPreference).where(DoctorPreference.doctor_id == doctor_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_preferences(self, doctor_id: uuid.UUID, **kwargs) -> DoctorPreference:
        existing = await self.get_preferences(doctor_id)
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing
        pref = DoctorPreference(doctor_id=doctor_id, **kwargs)
        self.session.add(pref)
        await self.session.flush()
        await self.session.refresh(pref)
        return pref
