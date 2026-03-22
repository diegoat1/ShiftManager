import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr


class CertificationTypeRead(BaseModel):
    id: int
    name: str
    description: str | None = None
    validity_months: int | None = None


class CertificationCreate(BaseModel):
    certification_type_id: int
    obtained_date: date
    expiry_date: date | None = None


class CertificationRead(BaseModel):
    id: int
    certification_type_id: int
    certification_type: CertificationTypeRead | None = None
    obtained_date: date
    expiry_date: date | None
    is_active: bool


class LanguageRead(BaseModel):
    id: int
    code: str
    name: str


class DoctorLanguageCreate(BaseModel):
    language_id: int
    proficiency_level: int = 3


class DoctorLanguageRead(BaseModel):
    id: int
    language_id: int
    language: LanguageRead | None = None
    proficiency_level: int


class DoctorPreferenceCreate(BaseModel):
    prefers_day: bool = True
    prefers_night: bool = False
    prefers_weekends: bool = False
    avoids_weekends: bool = False
    preferred_institution_types: str | None = None
    preferred_code_levels: str | None = None
    min_pay_per_shift: float | None = None
    max_preferred_distance_km: float | None = None


class DoctorPreferenceRead(BaseModel):
    id: int
    doctor_id: uuid.UUID
    prefers_day: bool
    prefers_night: bool
    prefers_weekends: bool
    avoids_weekends: bool
    preferred_institution_types: str | None
    preferred_code_levels: str | None
    min_pay_per_shift: float | None
    max_preferred_distance_km: float | None


class DoctorCreate(BaseModel):
    fiscal_code: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    password: str
    lat: float | None = None
    lon: float | None = None
    max_distance_km: float = 50.0
    willing_to_relocate: bool = False
    willing_overnight_stay: bool = False
    max_shifts_per_month: int = 20
    max_night_shifts_per_month: int | None = None
    max_code_level_id: int | None = None
    can_work_alone: bool = False
    can_emergency_vehicle: bool = False
    years_experience: int = 0


class DoctorUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    lat: float | None = None
    lon: float | None = None
    max_distance_km: float | None = None
    is_active: bool | None = None
    willing_to_relocate: bool | None = None
    willing_overnight_stay: bool | None = None
    max_shifts_per_month: int | None = None
    max_night_shifts_per_month: int | None = None
    max_code_level_id: int | None = None
    can_work_alone: bool | None = None
    can_emergency_vehicle: bool | None = None
    years_experience: int | None = None
    birth_date: date | None = None
    residence_address: str | None = None
    domicile_city: str | None = None
    ordine_province: str | None = None
    ordine_number: str | None = None
    has_own_vehicle: bool | None = None


class DoctorProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    lat: float | None = None
    lon: float | None = None
    max_distance_km: float | None = None
    willing_to_relocate: bool | None = None
    willing_overnight_stay: bool | None = None
    max_shifts_per_month: int | None = None
    max_night_shifts_per_month: int | None = None
    birth_date: date | None = None
    residence_address: str | None = None
    domicile_city: str | None = None
    ordine_province: str | None = None
    ordine_number: str | None = None
    has_own_vehicle: bool | None = None


class DoctorRead(BaseModel):
    id: uuid.UUID
    fiscal_code: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    lat: float | None
    lon: float | None
    max_distance_km: float
    is_active: bool
    willing_to_relocate: bool
    willing_overnight_stay: bool
    max_shifts_per_month: int
    max_night_shifts_per_month: int | None
    max_code_level_id: int | None
    can_work_alone: bool
    can_emergency_vehicle: bool
    years_experience: int
    birth_date: date | None = None
    residence_address: str | None = None
    domicile_city: str | None = None
    homologation_status: str | None = None
    ordine_province: str | None = None
    ordine_number: str | None = None
    has_own_vehicle: bool = False
    profile_completion_percent: int = 0
    created_at: datetime
    certifications: list[CertificationRead] = []
    languages: list[DoctorLanguageRead] = []
    preferences: DoctorPreferenceRead | None = None


class DoctorBrief(BaseModel):
    id: uuid.UUID
    fiscal_code: str
    first_name: str
    last_name: str
    email: str
    is_active: bool
