import uuid
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shift import Shift
from app.repositories.institution import InstitutionRepository
from app.repositories.shift import ShiftRepository
from app.schemas.shift import GenerateShiftsRequest, ShiftCreate, ShiftLanguageRequirementCreate, ShiftRequirementCreate, ShiftUpdate
from app.utils.enums import ShiftStatus


class ShiftService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ShiftRepository(session)
        self.inst_repo = InstitutionRepository(session)

    async def create(self, data: ShiftCreate) -> Shift:
        shift = await self.repo.create(**data.model_dump())

        # Copy institution requirements to shift
        site = await self.inst_repo.get_site(data.site_id)
        if site:
            inst_reqs = await self.inst_repo.get_requirements(site.institution_id)
            for req in inst_reqs:
                await self.repo.add_requirement(
                    shift.id,
                    certification_type_id=req.certification_type_id,
                    is_mandatory=req.is_mandatory,
                )
            lang_reqs = await self.inst_repo.get_language_requirements(site.institution_id)
            for req in lang_reqs:
                await self.repo.add_language_requirement(
                    shift.id,
                    language_id=req.language_id,
                    min_proficiency=req.min_proficiency,
                )
            # Inherit operational fields from site if not explicitly set on shift
            self._inherit_site_fields(shift, site)

        await self.session.commit()
        return await self.repo.get_with_requirements(shift.id)

    async def get(self, shift_id: uuid.UUID) -> Shift | None:
        return await self.repo.get_with_requirements(shift_id)

    async def get_all(self, skip: int = 0, limit: int = 50):
        items = await self.repo.get_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return items, total

    async def update(self, shift_id: uuid.UUID, data: ShiftUpdate) -> Shift | None:
        shift = await self.repo.get_by_id(shift_id)
        if not shift:
            return None
        await self.repo.update(shift, **data.model_dump(exclude_unset=True))
        await self.session.commit()
        return await self.repo.get_with_requirements(shift_id)

    async def delete(self, shift_id: uuid.UUID) -> bool:
        shift = await self.repo.get_by_id(shift_id)
        if not shift:
            return False
        await self.repo.delete(shift)
        await self.session.commit()
        return True

    async def add_requirement(self, shift_id: uuid.UUID, data: ShiftRequirementCreate):
        req = await self.repo.add_requirement(
            shift_id, certification_type_id=data.certification_type_id, is_mandatory=data.is_mandatory
        )
        await self.session.commit()
        return req

    async def add_language_requirement(self, shift_id: uuid.UUID, data: ShiftLanguageRequirementCreate):
        req = await self.repo.add_language_requirement(
            shift_id, language_id=data.language_id, min_proficiency=data.min_proficiency
        )
        await self.session.commit()
        return req

    @staticmethod
    def _inherit_site_fields(shift: Shift, site) -> None:
        """Copy operational fields from site to shift if not explicitly set."""
        if shift.min_code_level_id is None and site.min_code_level_id is not None:
            shift.min_code_level_id = site.min_code_level_id
        if not shift.requires_independent_work and site.requires_independent_work:
            shift.requires_independent_work = True
        if not shift.requires_emergency_vehicle and site.requires_emergency_vehicle:
            shift.requires_emergency_vehicle = True
        if shift.min_years_experience == 0 and site.min_years_experience > 0:
            shift.min_years_experience = site.min_years_experience

    async def get_calendar(self, site_id: uuid.UUID, start: date, end: date):
        return await self.repo.get_shifts_by_date_range(site_id, start, end)

    # Templates
    async def create_template(self, **kwargs):
        tmpl = await self.repo.create_template(**kwargs)
        await self.session.commit()
        return tmpl

    async def get_templates(self, site_id: uuid.UUID):
        return await self.repo.get_templates_by_site(site_id)

    async def delete_template(self, template_id: uuid.UUID) -> bool:
        tmpl = await self.repo.get_template(template_id)
        if not tmpl:
            return False
        await self.session.delete(tmpl)
        await self.session.commit()
        return True

    async def generate_shifts(self, data: GenerateShiftsRequest) -> list[Shift]:
        """Generate shifts from templates for a date range."""
        created = []
        current = data.start_date
        while current <= data.end_date:
            for tmpl_id in data.template_ids:
                tmpl = await self.repo.get_template(tmpl_id)
                if not tmpl:
                    continue
                start_dt = datetime.combine(current, tmpl.start_time)
                end_dt = datetime.combine(current, tmpl.end_time)
                if tmpl.end_time <= tmpl.start_time:
                    end_dt += timedelta(days=1)

                shift = await self.repo.create(
                    template_id=tmpl.id,
                    site_id=data.site_id,
                    date=current,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    required_doctors=tmpl.required_doctors,
                    base_pay=tmpl.base_pay,
                    is_night=tmpl.is_night,
                    min_code_level_id=tmpl.min_code_level_id,
                    requires_emergency_vehicle=tmpl.requires_emergency_vehicle,
                    status=ShiftStatus.OPEN,
                )

                # Copy institution requirements
                site = await self.inst_repo.get_site(data.site_id)
                if site:
                    inst_reqs = await self.inst_repo.get_requirements(site.institution_id)
                    for req in inst_reqs:
                        await self.repo.add_requirement(
                            shift.id,
                            certification_type_id=req.certification_type_id,
                            is_mandatory=req.is_mandatory,
                        )
                    lang_reqs = await self.inst_repo.get_language_requirements(site.institution_id)
                    for req in lang_reqs:
                        await self.repo.add_language_requirement(
                            shift.id, language_id=req.language_id, min_proficiency=req.min_proficiency
                        )
                    # Inherit operational fields from site
                    self._inherit_site_fields(shift, site)

                created.append(shift)
            current += timedelta(days=1)

        await self.session.commit()
        return created
