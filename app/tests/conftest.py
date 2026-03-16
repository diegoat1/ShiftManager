import uuid
from datetime import date, datetime, time, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_session
from app.main import app
from app.models.doctor import CertificationType, Doctor, DoctorCertification, DoctorLanguage, Language
from app.models.institution import Institution, InstitutionSite
from app.models.requirement import CodeLevel, InstitutionLanguageRequirement, InstitutionRequirement
from app.models.shift import Shift, ShiftLanguageRequirement, ShiftRequirement
from app.models.availability import DoctorAvailability
from app.core.security import hash_password
from app.utils.enums import AvailabilityType, ShiftStatus

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def session():
    async with TestSession() as session:
        yield session


@pytest.fixture
async def client(session):
    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def seed_lookups(session: AsyncSession):
    """Seed certification types, languages, and code levels."""
    cert_bls = CertificationType(name="BLS", description="Basic Life Support", validity_months=24)
    cert_acls = CertificationType(name="ACLS", description="Advanced Cardiovascular Life Support", validity_months=24)
    lang_it = Language(code="it", name="Italiano")
    lang_en = Language(code="en", name="English")
    cl_white = CodeLevel(code="WHITE", description="Codice Bianco", severity_order=1)
    cl_green = CodeLevel(code="GREEN", description="Codice Verde", severity_order=2)
    cl_yellow = CodeLevel(code="YELLOW", description="Codice Giallo", severity_order=3)
    cl_red = CodeLevel(code="RED", description="Codice Rosso", severity_order=4)
    session.add_all([cert_bls, cert_acls, lang_it, lang_en, cl_white, cl_green, cl_yellow, cl_red])
    await session.flush()
    return {
        "cert_bls": cert_bls, "cert_acls": cert_acls,
        "lang_it": lang_it, "lang_en": lang_en,
        "cl_white": cl_white, "cl_green": cl_green, "cl_yellow": cl_yellow, "cl_red": cl_red,
    }


@pytest.fixture
async def sample_doctor(session: AsyncSession, seed_lookups):
    lookups = seed_lookups
    doctor = Doctor(
        fiscal_code="RSSMRA80A01H501Z",
        first_name="Mario",
        last_name="Rossi",
        email="mario@example.com",
        password_hash=hash_password("password123"),
        lat=41.9028,
        lon=12.4964,
        max_distance_km=50.0,
        is_active=True,
    )
    session.add(doctor)
    await session.flush()

    # Add BLS certification (valid)
    cert = DoctorCertification(
        doctor_id=doctor.id,
        certification_type_id=lookups["cert_bls"].id,
        obtained_date=date(2025, 1, 1),
        expiry_date=date(2027, 1, 1),
        is_active=True,
    )
    session.add(cert)

    # Add Italian language
    lang = DoctorLanguage(
        doctor_id=doctor.id,
        language_id=lookups["lang_it"].id,
        proficiency_level=5,
    )
    session.add(lang)
    await session.flush()
    return doctor


@pytest.fixture
async def sample_institution(session: AsyncSession):
    inst = Institution(
        name="Ospedale San Camillo",
        tax_code="12345678901",
        address="Via Roma 1",
        city="Roma",
        province="RM",
    )
    session.add(inst)
    await session.flush()

    site = InstitutionSite(
        institution_id=inst.id,
        name="Pronto Soccorso",
        address="Via Roma 1",
        city="Roma",
        province="RM",
        lat=41.8800,
        lon=12.4700,
    )
    session.add(site)
    await session.flush()
    return {"institution": inst, "site": site}


@pytest.fixture
async def sample_shift(session: AsyncSession, sample_institution, seed_lookups):
    site = sample_institution["site"]
    lookups = seed_lookups

    shift = Shift(
        site_id=site.id,
        date=date(2026, 4, 1),
        start_datetime=datetime(2026, 4, 1, 8, 0),
        end_datetime=datetime(2026, 4, 1, 20, 0),
        required_doctors=1,
        status=ShiftStatus.OPEN,
        base_pay=500.0,
        is_night=False,
    )
    session.add(shift)
    await session.flush()

    # Add BLS requirement
    req = ShiftRequirement(
        shift_id=shift.id,
        certification_type_id=lookups["cert_bls"].id,
        is_mandatory=True,
    )
    session.add(req)

    # Add Italian language requirement
    lang_req = ShiftLanguageRequirement(
        shift_id=shift.id,
        language_id=lookups["lang_it"].id,
        min_proficiency=3,
    )
    session.add(lang_req)
    await session.flush()
    return shift


@pytest.fixture
async def sample_availability(session: AsyncSession, sample_doctor):
    avail = DoctorAvailability(
        doctor_id=sample_doctor.id,
        date=date(2026, 4, 1),
        start_time=time(0, 0),
        end_time=time(23, 59),
        availability_type=AvailabilityType.AVAILABLE,
    )
    session.add(avail)
    await session.flush()
    return avail
