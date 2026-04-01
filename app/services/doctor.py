import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.doctor import CertificationType, Doctor, DoctorPreference, Language
from app.repositories.doctor import DoctorRepository
from app.schemas.doctor import CertificationCreate, DoctorCreate, DoctorLanguageCreate, DoctorPreferenceCreate, DoctorUpdate


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

        return await self.repo.get_with_relations(doctor.id)

    async def get_by_user_id(self, user_id: uuid.UUID) -> Doctor | None:
        stmt = select(Doctor).where(Doctor.user_id == user_id)
        result = await self.session.execute(stmt)
        doctor = result.scalar_one_or_none()
        if doctor:
            return await self.repo.get_with_relations(doctor.id)
        return None

    async def update_profile(self, doctor_id: uuid.UUID, data) -> Doctor | None:
        doctor = await self.repo.get_by_id(doctor_id)
        if not doctor:
            return None
        updates = data.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(doctor, key, value)
        doctor.profile_completion_percent = self._calc_profile_completion(doctor)
        await self.session.flush()

        return await self.repo.get_with_relations(doctor_id)

    @staticmethod
    def _calc_profile_completion(doctor: Doctor) -> int:
        fields = [
            doctor.first_name, doctor.last_name, doctor.email,
            doctor.fiscal_code, doctor.phone, doctor.birth_date,
            doctor.residence_address, doctor.domicile_city,
            doctor.ordine_province, doctor.ordine_number,
            doctor.lat, doctor.lon,
        ]
        filled = sum(1 for f in fields if f is not None and f != "")
        return int(filled / len(fields) * 100)

    async def get(self, doctor_id: uuid.UUID) -> Doctor | None:
        return await self.repo.get_with_relations(doctor_id)

    async def get_all(self, skip: int = 0, limit: int = 50, search: str | None = None):
        doctors = await self.repo.get_all(skip=skip, limit=limit, search=search)
        total = await self.repo.count(search=search)
        return doctors, total

    async def update(self, doctor_id: uuid.UUID, data: DoctorUpdate) -> Doctor | None:
        doctor = await self.repo.get_by_id(doctor_id)
        if not doctor:
            return None
        await self.repo.update(doctor, **data.model_dump(exclude_unset=True))

        return await self.repo.get_with_relations(doctor_id)

    async def delete(self, doctor_id: uuid.UUID) -> bool:
        doctor = await self.repo.get_by_id(doctor_id)
        if not doctor:
            return False
        await self.repo.delete(doctor)

        return True

    async def add_certification(self, doctor_id: uuid.UUID, data: CertificationCreate):
        cert = await self.repo.add_certification(
            doctor_id=doctor_id,
            certification_type_id=data.certification_type_id,
            obtained_date=data.obtained_date,
            expiry_date=data.expiry_date,
        )

        return cert

    async def remove_certification(self, doctor_id: uuid.UUID, cert_type_id: int) -> bool:
        result = await self.repo.remove_certification(doctor_id, cert_type_id)

        return result

    async def add_language(self, doctor_id: uuid.UUID, data: DoctorLanguageCreate):
        lang = await self.repo.add_language(
            doctor_id=doctor_id,
            language_id=data.language_id,
            proficiency_level=data.proficiency_level,
        )

        return lang

    async def remove_language(self, doctor_id: uuid.UUID, language_id: int) -> bool:
        result = await self.repo.remove_language(doctor_id, language_id)

        return result

    async def get_certifications(self, doctor_id: uuid.UUID):
        return await self.repo.get_certifications(doctor_id)

    async def get_languages(self, doctor_id: uuid.UUID):
        return await self.repo.get_languages(doctor_id)

    async def get_preferences(self, doctor_id: uuid.UUID) -> DoctorPreference | None:
        return await self.repo.get_preferences(doctor_id)

    async def upsert_preferences(self, doctor_id: uuid.UUID, data: DoctorPreferenceCreate) -> DoctorPreference:
        pref = await self.repo.upsert_preferences(doctor_id, **data.model_dump())

        return pref
