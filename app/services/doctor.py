import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.doctor import CertificationType, Doctor, Language
from app.repositories.doctor import DoctorRepository
from app.schemas.doctor import CertificationCreate, DoctorCreate, DoctorLanguageCreate, DoctorUpdate


class DoctorService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DoctorRepository(session)

    async def create(self, data: DoctorCreate) -> Doctor:
        doctor = await self.repo.create(
            fiscal_code=data.fiscal_code,
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            phone=data.phone,
            password_hash=hash_password(data.password),
            lat=data.lat,
            lon=data.lon,
            max_distance_km=data.max_distance_km,
            willing_to_relocate=data.willing_to_relocate,
            willing_overnight_stay=data.willing_overnight_stay,
            max_shifts_per_month=data.max_shifts_per_month,
            max_night_shifts_per_month=data.max_night_shifts_per_month,
            max_code_level_id=data.max_code_level_id,
            can_work_alone=data.can_work_alone,
            can_emergency_vehicle=data.can_emergency_vehicle,
            years_experience=data.years_experience,
        )
        await self.session.commit()
        return await self.repo.get_with_relations(doctor.id)

    async def get(self, doctor_id: uuid.UUID) -> Doctor | None:
        return await self.repo.get_with_relations(doctor_id)

    async def get_all(self, skip: int = 0, limit: int = 50):
        doctors = await self.repo.get_all(skip=skip, limit=limit)
        total = await self.repo.count()
        return doctors, total

    async def update(self, doctor_id: uuid.UUID, data: DoctorUpdate) -> Doctor | None:
        doctor = await self.repo.get_by_id(doctor_id)
        if not doctor:
            return None
        await self.repo.update(doctor, **data.model_dump(exclude_unset=True))
        await self.session.commit()
        return await self.repo.get_with_relations(doctor_id)

    async def delete(self, doctor_id: uuid.UUID) -> bool:
        doctor = await self.repo.get_by_id(doctor_id)
        if not doctor:
            return False
        await self.repo.delete(doctor)
        await self.session.commit()
        return True

    async def add_certification(self, doctor_id: uuid.UUID, data: CertificationCreate):
        cert = await self.repo.add_certification(
            doctor_id=doctor_id,
            certification_type_id=data.certification_type_id,
            obtained_date=data.obtained_date,
            expiry_date=data.expiry_date,
        )
        await self.session.commit()
        return cert

    async def remove_certification(self, doctor_id: uuid.UUID, cert_type_id: int) -> bool:
        result = await self.repo.remove_certification(doctor_id, cert_type_id)
        await self.session.commit()
        return result

    async def add_language(self, doctor_id: uuid.UUID, data: DoctorLanguageCreate):
        lang = await self.repo.add_language(
            doctor_id=doctor_id,
            language_id=data.language_id,
            proficiency_level=data.proficiency_level,
        )
        await self.session.commit()
        return lang

    async def remove_language(self, doctor_id: uuid.UUID, language_id: int) -> bool:
        result = await self.repo.remove_language(doctor_id, language_id)
        await self.session.commit()
        return result
