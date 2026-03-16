"""Tests for extended eligibility checks — Italian medical context."""
import uuid
from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import ShiftAssignment
from app.models.availability import DoctorAvailability
from app.models.doctor import Doctor, DoctorCertification, DoctorLanguage
from app.models.shift import Shift
from app.core.security import hash_password
from app.rules.eligibility import EligibilityEngine
from app.utils.enums import AssignmentStatus, AvailabilityType, ShiftStatus


def _make_doctor(session, seed_lookups, **overrides):
    """Helper to create a doctor with defaults + overrides."""
    defaults = dict(
        fiscal_code=f"TEST{uuid.uuid4().hex[:12].upper()}",
        first_name="Test",
        last_name="Doctor",
        email=f"test.{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("pass"),
        lat=41.9028,
        lon=12.4964,
        max_distance_km=50.0,
        is_active=True,
        years_experience=5,
        can_work_alone=True,
        can_emergency_vehicle=True,
        max_shifts_per_month=20,
        max_night_shifts_per_month=None,
        max_code_level_id=None,
    )
    defaults.update(overrides)
    doctor = Doctor(**defaults)
    session.add(doctor)
    return doctor


async def _setup_doctor_shift(session, seed_lookups, sample_institution, doctor_overrides=None, shift_overrides=None):
    """Create a doctor, shift, and availability for testing."""
    lookups = seed_lookups
    site = sample_institution["site"]

    doctor = _make_doctor(session, lookups, **(doctor_overrides or {}))
    await session.flush()

    # Add BLS cert + Italian language so base checks pass
    session.add(DoctorCertification(
        doctor_id=doctor.id, certification_type_id=lookups["cert_bls"].id,
        obtained_date=date(2025, 1, 1), expiry_date=date(2027, 1, 1), is_active=True,
    ))
    session.add(DoctorLanguage(
        doctor_id=doctor.id, language_id=lookups["lang_it"].id, proficiency_level=5,
    ))
    session.add(DoctorAvailability(
        doctor_id=doctor.id, date=date(2026, 4, 1),
        start_time=time(0, 0), end_time=time(23, 59),
        availability_type=AvailabilityType.AVAILABLE,
    ))

    shift_defaults = dict(
        site_id=site.id,
        date=date(2026, 4, 1),
        start_datetime=datetime(2026, 4, 1, 8, 0),
        end_datetime=datetime(2026, 4, 1, 20, 0),
        required_doctors=1,
        status=ShiftStatus.OPEN,
        base_pay=500.0,
        is_night=False,
    )
    shift_defaults.update(shift_overrides or {})
    shift = Shift(**shift_defaults)
    session.add(shift)
    await session.flush()

    return doctor, shift


@pytest.mark.asyncio
async def test_code_level_insufficient(session, seed_lookups, sample_institution):
    """Doctor's max code level is below shift's requirement."""
    lookups = seed_lookups
    doctor, shift = await _setup_doctor_shift(
        session, lookups, sample_institution,
        doctor_overrides={"max_code_level_id": lookups["cl_green"].id},
        shift_overrides={"min_code_level_id": lookups["cl_red"].id},
    )
    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(doctor.id, shift.id)
    assert is_eligible is False
    assert any("code level" in r.lower() for r in reasons)


@pytest.mark.asyncio
async def test_code_level_sufficient(session, seed_lookups, sample_institution):
    """Doctor's max code level meets shift's requirement."""
    lookups = seed_lookups
    doctor, shift = await _setup_doctor_shift(
        session, lookups, sample_institution,
        doctor_overrides={"max_code_level_id": lookups["cl_red"].id},
        shift_overrides={"min_code_level_id": lookups["cl_yellow"].id},
    )
    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(doctor.id, shift.id)
    assert is_eligible is True
    assert len(reasons) == 0


@pytest.mark.asyncio
async def test_independent_work_required(session, seed_lookups, sample_institution):
    """Shift requires independent work but doctor can't work alone."""
    lookups = seed_lookups
    doctor, shift = await _setup_doctor_shift(
        session, lookups, sample_institution,
        doctor_overrides={"can_work_alone": False},
        shift_overrides={"requires_independent_work": True},
    )
    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(doctor.id, shift.id)
    assert is_eligible is False
    assert any("independent work" in r.lower() for r in reasons)


@pytest.mark.asyncio
async def test_emergency_vehicle_required(session, seed_lookups, sample_institution):
    """Shift requires emergency vehicle but doctor lacks capability."""
    lookups = seed_lookups
    doctor, shift = await _setup_doctor_shift(
        session, lookups, sample_institution,
        doctor_overrides={"can_emergency_vehicle": False},
        shift_overrides={"requires_emergency_vehicle": True},
    )
    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(doctor.id, shift.id)
    assert is_eligible is False
    assert any("emergency vehicle" in r.lower() for r in reasons)


@pytest.mark.asyncio
async def test_years_experience_insufficient(session, seed_lookups, sample_institution):
    """Doctor doesn't have enough years of experience."""
    lookups = seed_lookups
    doctor, shift = await _setup_doctor_shift(
        session, lookups, sample_institution,
        doctor_overrides={"years_experience": 1},
        shift_overrides={"min_years_experience": 5},
    )
    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(doctor.id, shift.id)
    assert is_eligible is False
    assert any("experience" in r.lower() for r in reasons)


@pytest.mark.asyncio
async def test_monthly_shift_limit_exceeded(session, seed_lookups, sample_institution):
    """Doctor has reached their monthly shift limit."""
    lookups = seed_lookups
    site = sample_institution["site"]

    doctor = _make_doctor(session, lookups, max_shifts_per_month=3)
    await session.flush()

    session.add(DoctorCertification(
        doctor_id=doctor.id, certification_type_id=lookups["cert_bls"].id,
        obtained_date=date(2025, 1, 1), expiry_date=date(2027, 1, 1), is_active=True,
    ))
    session.add(DoctorLanguage(
        doctor_id=doctor.id, language_id=lookups["lang_it"].id, proficiency_level=5,
    ))

    # Create 3 existing shifts with assignments in April
    for i in range(3):
        d = date(2026, 4, 2 + i * 3)
        s = Shift(
            site_id=site.id, date=d,
            start_datetime=datetime.combine(d, time(8, 0)),
            end_datetime=datetime.combine(d, time(14, 0)),
            status=ShiftStatus.OPEN,
        )
        session.add(s)
        await session.flush()
        session.add(ShiftAssignment(
            shift_id=s.id, doctor_id=doctor.id,
            status=AssignmentStatus.CONFIRMED, pay_amount=300.0,
        ))
        session.add(DoctorAvailability(
            doctor_id=doctor.id, date=d,
            start_time=time(0, 0), end_time=time(23, 59),
        ))

    # The target shift on April 15
    target_date = date(2026, 4, 15)
    target_shift = Shift(
        site_id=site.id, date=target_date,
        start_datetime=datetime(2026, 4, 15, 8, 0),
        end_datetime=datetime(2026, 4, 15, 14, 0),
        status=ShiftStatus.OPEN,
    )
    session.add(target_shift)
    session.add(DoctorAvailability(
        doctor_id=doctor.id, date=target_date,
        start_time=time(0, 0), end_time=time(23, 59),
    ))
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(doctor.id, target_shift.id)
    assert is_eligible is False
    assert any("Monthly shift limit" in r for r in reasons)


@pytest.mark.asyncio
async def test_personal_night_shift_limit(session, seed_lookups, sample_institution):
    """Doctor has a personal night shift limit lower than global."""
    lookups = seed_lookups
    site = sample_institution["site"]

    doctor = _make_doctor(session, lookups, max_night_shifts_per_month=2)
    await session.flush()

    session.add(DoctorCertification(
        doctor_id=doctor.id, certification_type_id=lookups["cert_bls"].id,
        obtained_date=date(2025, 1, 1), expiry_date=date(2027, 1, 1), is_active=True,
    ))
    session.add(DoctorLanguage(
        doctor_id=doctor.id, language_id=lookups["lang_it"].id, proficiency_level=5,
    ))

    # Create 2 existing night shifts with assignments
    for i in range(2):
        d = date(2026, 4, 2 + i * 5)
        s = Shift(
            site_id=site.id, date=d,
            start_datetime=datetime.combine(d, time(20, 0)),
            end_datetime=datetime.combine(d + timedelta(days=1), time(6, 0)),
            status=ShiftStatus.OPEN, is_night=True,
        )
        session.add(s)
        await session.flush()
        session.add(ShiftAssignment(
            shift_id=s.id, doctor_id=doctor.id,
            status=AssignmentStatus.CONFIRMED, pay_amount=400.0,
        ))
        session.add(DoctorAvailability(
            doctor_id=doctor.id, date=d,
            start_time=time(0, 0), end_time=time(23, 59),
        ))

    # Target night shift
    target_date = date(2026, 4, 20)
    target_shift = Shift(
        site_id=site.id, date=target_date,
        start_datetime=datetime.combine(target_date, time(20, 0)),
        end_datetime=datetime.combine(target_date + timedelta(days=1), time(6, 0)),
        status=ShiftStatus.OPEN, is_night=True,
    )
    session.add(target_shift)
    session.add(DoctorAvailability(
        doctor_id=doctor.id, date=target_date,
        start_time=time(0, 0), end_time=time(23, 59),
    ))
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(doctor.id, target_shift.id)
    assert is_eligible is False
    assert any("Personal night shift limit" in r for r in reasons)


@pytest.mark.asyncio
async def test_distance_with_relocation(session, seed_lookups, sample_institution):
    """Doctor is far but willing to relocate — warning instead of failure."""
    lookups = seed_lookups
    site = sample_institution["site"]

    doctor = _make_doctor(session, lookups,
        lat=45.4642, lon=9.1900,  # Milan
        max_distance_km=10.0,
        willing_to_relocate=True,
    )
    await session.flush()

    session.add(DoctorCertification(
        doctor_id=doctor.id, certification_type_id=lookups["cert_bls"].id,
        obtained_date=date(2025, 1, 1), expiry_date=date(2027, 1, 1), is_active=True,
    ))
    session.add(DoctorLanguage(
        doctor_id=doctor.id, language_id=lookups["lang_it"].id, proficiency_level=5,
    ))
    session.add(DoctorAvailability(
        doctor_id=doctor.id, date=date(2026, 4, 1),
        start_time=time(0, 0), end_time=time(23, 59),
    ))

    shift = Shift(
        site_id=site.id,
        date=date(2026, 4, 1),
        start_datetime=datetime(2026, 4, 1, 8, 0),
        end_datetime=datetime(2026, 4, 1, 20, 0),
        status=ShiftStatus.OPEN,
    )
    session.add(shift)
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, warnings = await engine.check(doctor.id, shift.id)
    assert is_eligible is True  # Not a failure, just a warning
    assert any("relocate" in w.lower() for w in warnings)
