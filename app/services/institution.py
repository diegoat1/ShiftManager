import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.institution import Institution, InstitutionSite
from app.repositories.institution import InstitutionRepository
from app.schemas.institution import (
    InstitutionCreate,
    InstitutionUpdate,
    LanguageRequirementCreate,
    RequirementCreate,
    SiteCreate,
    SiteUpdate,
)


class InstitutionService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = InstitutionRepository(session)

    async def create(self, data: InstitutionCreate) -> Institution:
        inst = await self.repo.create(**data.model_dump())

        return await self.repo.get_with_sites(inst.id)

    async def get(self, institution_id: uuid.UUID) -> Institution | None:
        return await self.repo.get_with_sites(institution_id)

    async def get_all(self, skip: int = 0, limit: int = 50):
        items = await self.repo.get_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def update(self, institution_id: uuid.UUID, data: InstitutionUpdate) -> Institution | None:
        inst = await self.repo.get_by_id(institution_id)
        if not inst:
            return None
        await self.repo.update(inst, **data.model_dump(exclude_unset=True))

        return await self.repo.get_with_sites(institution_id)

    async def delete(self, institution_id: uuid.UUID) -> bool:
        inst = await self.repo.get_by_id(institution_id)
        if not inst:
            return False
        await self.repo.delete(inst)

        return True

    # Sites
    async def create_site(self, institution_id: uuid.UUID, data: SiteCreate) -> InstitutionSite:
        site = await self.repo.create_site(institution_id, **data.model_dump())

        return site

    async def get_site(self, site_id: uuid.UUID) -> InstitutionSite | None:
        return await self.repo.get_site(site_id)

    async def update_site(self, site_id: uuid.UUID, data: SiteUpdate) -> InstitutionSite | None:
        site = await self.repo.get_site(site_id)
        if not site:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(site, key, value)
        await self.session.flush()

        return site

    async def get_sites(self, institution_id: uuid.UUID):
        return await self.repo.get_sites_by_institution(institution_id)

    async def delete_site(self, site_id: uuid.UUID) -> bool:
        site = await self.repo.get_site(site_id)
        if not site:
            return False
        await self.session.delete(site)

        return True

    # Requirements
    async def add_requirement(self, institution_id: uuid.UUID, data: RequirementCreate):
        req = await self.repo.add_requirement(
            institution_id, certification_type_id=data.certification_type_id, is_mandatory=data.is_mandatory
        )

        return req

    async def get_requirements(self, institution_id: uuid.UUID):
        return await self.repo.get_requirements(institution_id)

    async def add_language_requirement(self, institution_id: uuid.UUID, data: LanguageRequirementCreate):
        req = await self.repo.add_language_requirement(
            institution_id, language_id=data.language_id, min_proficiency=data.min_proficiency
        )

        return req

    async def get_language_requirements(self, institution_id: uuid.UUID):
        return await self.repo.get_language_requirements(institution_id)
