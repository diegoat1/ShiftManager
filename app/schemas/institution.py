import uuid
from datetime import datetime

from pydantic import BaseModel


class InstitutionCreate(BaseModel):
    name: str
    tax_code: str
    address: str | None = None
    city: str | None = None
    province: str | None = None
    institution_type: str | None = None
    cooperative_id: uuid.UUID | None = None


class InstitutionUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    institution_type: str | None = None
    is_active: bool | None = None
    cooperative_id: uuid.UUID | None = None


class SiteCreate(BaseModel):
    name: str
    address: str | None = None
    city: str | None = None
    province: str | None = None
    lat: float | None = None
    lon: float | None = None
    lodging_available: bool = False
    meal_support: bool = False
    parking_available: bool = False
    min_code_level_id: int | None = None
    requires_independent_work: bool = False
    requires_emergency_vehicle: bool = False
    min_years_experience: int = 0


class SiteUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    city: str | None = None
    province: str | None = None
    lat: float | None = None
    lon: float | None = None
    is_active: bool | None = None
    lodging_available: bool | None = None
    meal_support: bool | None = None
    parking_available: bool | None = None
    min_code_level_id: int | None = None
    requires_independent_work: bool | None = None
    requires_emergency_vehicle: bool | None = None
    min_years_experience: int | None = None


class SiteRead(BaseModel):
    id: uuid.UUID
    institution_id: uuid.UUID
    name: str
    address: str | None
    city: str | None
    province: str | None
    lat: float | None
    lon: float | None
    is_active: bool
    lodging_available: bool
    meal_support: bool
    parking_available: bool
    min_code_level_id: int | None
    requires_independent_work: bool
    requires_emergency_vehicle: bool
    min_years_experience: int
    created_at: datetime


class InstitutionRead(BaseModel):
    id: uuid.UUID
    name: str
    tax_code: str
    address: str | None
    city: str | None
    province: str | None
    institution_type: str | None
    is_active: bool
    cooperative_id: uuid.UUID | None = None
    created_at: datetime
    sites: list[SiteRead] = []


class RequirementCreate(BaseModel):
    certification_type_id: int
    is_mandatory: bool = True


class RequirementRead(BaseModel):
    id: int
    institution_id: uuid.UUID
    certification_type_id: int
    is_mandatory: bool


class LanguageRequirementCreate(BaseModel):
    language_id: int
    min_proficiency: int = 3


class LanguageRequirementRead(BaseModel):
    id: int
    institution_id: uuid.UUID
    language_id: int
    min_proficiency: int
