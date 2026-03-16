import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.institution import Institution, InstitutionSite
from app.models.requirement import InstitutionLanguageRequirement, InstitutionRequirement
from app.repositories.base import BaseRepository


class InstitutionRepository(BaseRepository[Institution]):
    def __init__(self, session: AsyncSession):
        super().__init__(Institution, session)

    async def get_with_sites(self, institution_id: uuid.UUID) -> Institution | None:
        stmt = (
            select(Institution)
            .options(selectinload(Institution.sites))
            .where(Institution.id == institution_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_tax_code(self, tax_code: str) -> Institution | None:
        result = await self.session.execute(select(Institution).where(Institution.tax_code == tax_code))
        return result.scalar_one_or_none()

    # Sites
    async def create_site(self, institution_id: uuid.UUID, **kwargs) -> InstitutionSite:
        site = InstitutionSite(institution_id=institution_id, **kwargs)
        self.session.add(site)
        await self.session.flush()
        await self.session.refresh(site)
        return site

    async def get_site(self, site_id: uuid.UUID) -> InstitutionSite | None:
        return await self.session.get(InstitutionSite, site_id)

    async def get_sites_by_institution(self, institution_id: uuid.UUID) -> Sequence[InstitutionSite]:
        result = await self.session.execute(
            select(InstitutionSite).where(InstitutionSite.institution_id == institution_id)
        )
        return result.scalars().all()

    # Requirements
    async def add_requirement(self, institution_id: uuid.UUID, **kwargs) -> InstitutionRequirement:
        req = InstitutionRequirement(institution_id=institution_id, **kwargs)
        self.session.add(req)
        await self.session.flush()
        await self.session.refresh(req)
        return req

    async def get_requirements(self, institution_id: uuid.UUID) -> Sequence[InstitutionRequirement]:
        result = await self.session.execute(
            select(InstitutionRequirement).where(InstitutionRequirement.institution_id == institution_id)
        )
        return result.scalars().all()

    async def add_language_requirement(self, institution_id: uuid.UUID, **kwargs) -> InstitutionLanguageRequirement:
        req = InstitutionLanguageRequirement(institution_id=institution_id, **kwargs)
        self.session.add(req)
        await self.session.flush()
        await self.session.refresh(req)
        return req

    async def get_language_requirements(self, institution_id: uuid.UUID) -> Sequence[InstitutionLanguageRequirement]:
        result = await self.session.execute(
            select(InstitutionLanguageRequirement).where(
                InstitutionLanguageRequirement.institution_id == institution_id
            )
        )
        return result.scalars().all()
