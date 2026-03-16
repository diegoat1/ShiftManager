"""Tests for the eligibility engine — covers all 10 constraint checks."""
import uuid
from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import ShiftAssignment
from app.models.availability import DoctorAvailability, DoctorUnavailability
from app.models.doctor import Doctor, DoctorCertification, DoctorLanguage
from app.models.shift import Shift, ShiftLanguageRequirement, ShiftRequirement
from app.core.security import hash_password
from app.rules.eligibility import EligibilityEngine
from app.utils.enums import AssignmentStatus, AvailabilityType, ShiftStatus, UnavailabilityReason


@pytest.mark.asyncio
async def test_eligible_doctor(session, sample_doctor, sample_shift, sample_availability, seed_lookups):
    engine = EligibilityEngine(session)
    is_eligible, reasons, warnings = await engine.check(sample_doctor.id, sample_shift.id)
    assert is_eligible is True
    assert len(reasons) == 0


@pytest.mark.asyncio
async def test_inactive_doctor(session, sample_doctor, sample_shift, sample_availability, seed_lookups):
    sample_doctor.is_active = False
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(sample_doctor.id, sample_shift.id)
    assert is_eligible is False
    assert any("not active" in r for r in reasons)


@pytest.mark.asyncio
async def test_no_availability(session, sample_doctor, sample_shift, seed_lookups):
    # No availability set for doctor
    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(sample_doctor.id, sample_shift.id)
    assert is_eligible is False
    assert any("not available" in r for r in reasons)


@pytest.mark.asyncio
async def test_missing_certification(session, sample_institution, seed_lookups, sample_availability):
    lookups = seed_lookups
    # Doctor without ACLS
    doctor = Doctor(
        fiscal_code="NOCERT00A01H501Z",
        first_name="No",
        last_name="Cert",
        email="nocert@test.com",
        password_hash=hash_password("pass"),
        lat=41.9,
        lon=12.5,
        is_active=True,
    )
    session.add(doctor)
    await session.flush()

    # Create shift that requires ACLS
    shift = Shift(
        site_id=sample_institution["site"].id,
        date=date(2026, 4, 1),
        start_datetime=datetime(2026, 4, 1, 8, 0),
        end_datetime=datetime(2026, 4, 1, 20, 0),
        status=ShiftStatus.OPEN,
    )
    session.add(shift)
    await session.flush()

    req = ShiftRequirement(
        shift_id=shift.id,
        certification_type_id=lookups["cert_acls"].id,
        is_mandatory=True,
    )
    session.add(req)

    avail = DoctorAvailability(
        doctor_id=doctor.id,
        date=date(2026, 4, 1),
        start_time=time(0, 0),
        end_time=time(23, 59),
    )
    session.add(avail)
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(doctor.id, shift.id)
    assert is_eligible is False
    assert any("Missing mandatory certification" in r for r in reasons)


@pytest.mark.asyncio
async def test_expired_certification(session, sample_doctor, sample_shift, sample_availability, seed_lookups):
    # Expire the BLS cert
    await session.refresh(sample_doctor, ["certifications"])
    for cert in sample_doctor.certifications:
        cert.expiry_date = date(2025, 1, 1)  # expired
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(sample_doctor.id, sample_shift.id)
    assert is_eligible is False
    assert any("expired" in r.lower() for r in reasons)


@pytest.mark.asyncio
async def test_missing_language(session, sample_institution, seed_lookups, sample_availability):
    lookups = seed_lookups
    doctor = Doctor(
        fiscal_code="NOLANG00A01H501Z",
        first_name="No",
        last_name="Lang",
        email="nolang@test.com",
        password_hash=hash_password("pass"),
        lat=41.9,
        lon=12.5,
        is_active=True,
    )
    session.add(doctor)
    await session.flush()

    shift = Shift(
        site_id=sample_institution["site"].id,
        date=date(2026, 4, 1),
        start_datetime=datetime(2026, 4, 1, 8, 0),
        end_datetime=datetime(2026, 4, 1, 20, 0),
        status=ShiftStatus.OPEN,
    )
    session.add(shift)
    await session.flush()

    lang_req = ShiftLanguageRequirement(
        shift_id=shift.id,
        language_id=lookups["lang_en"].id,
        min_proficiency=3,
    )
    session.add(lang_req)

    avail = DoctorAvailability(
        doctor_id=doctor.id,
        date=date(2026, 4, 1),
        start_time=time(0, 0),
        end_time=time(23, 59),
    )
    session.add(avail)
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(doctor.id, shift.id)
    assert is_eligible is False
    assert any("Missing required language" in r for r in reasons)


@pytest.mark.asyncio
async def test_distance_exceeded(session, sample_shift, sample_availability, seed_lookups):
    # Doctor far away
    doctor = Doctor(
        fiscal_code="FARAWAY0A01H501Z",
        first_name="Far",
        last_name="Away",
        email="far@test.com",
        password_hash=hash_password("pass"),
        lat=45.4642,  # Milan
        lon=9.1900,
        max_distance_km=10.0,  # Very short range
        is_active=True,
    )
    session.add(doctor)
    await session.flush()

    # Add required certs and language
    lookups = seed_lookups
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
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(doctor.id, sample_shift.id)
    assert is_eligible is False
    assert any("Distance" in r for r in reasons)


@pytest.mark.asyncio
async def test_shift_overlap(session, sample_doctor, sample_shift, sample_institution, sample_availability, seed_lookups):
    # Assign doctor to sample shift
    assignment = ShiftAssignment(
        shift_id=sample_shift.id,
        doctor_id=sample_doctor.id,
        status=AssignmentStatus.CONFIRMED,
        pay_amount=500.0,
    )
    session.add(assignment)

    # Create overlapping shift
    shift2 = Shift(
        site_id=sample_institution["site"].id,
        date=date(2026, 4, 1),
        start_datetime=datetime(2026, 4, 1, 10, 0),
        end_datetime=datetime(2026, 4, 1, 18, 0),
        status=ShiftStatus.OPEN,
    )
    session.add(shift2)
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(sample_doctor.id, shift2.id)
    assert is_eligible is False
    assert any("Overlaps" in r for r in reasons)


@pytest.mark.asyncio
async def test_rest_period_violation(session, sample_doctor, sample_shift, sample_institution, sample_availability, seed_lookups):
    # Assign doctor to sample shift (08:00-20:00)
    assignment = ShiftAssignment(
        shift_id=sample_shift.id,
        doctor_id=sample_doctor.id,
        status=AssignmentStatus.CONFIRMED,
        pay_amount=500.0,
    )
    session.add(assignment)

    # Create shift starting 5 hours after (should violate 11h rest)
    shift2 = Shift(
        site_id=sample_institution["site"].id,
        date=date(2026, 4, 2),
        start_datetime=datetime(2026, 4, 2, 1, 0),  # 5h gap from 20:00
        end_datetime=datetime(2026, 4, 2, 8, 0),
        status=ShiftStatus.OPEN,
    )
    session.add(shift2)

    avail2 = DoctorAvailability(
        doctor_id=sample_doctor.id,
        date=date(2026, 4, 2),
        start_time=time(0, 0),
        end_time=time(23, 59),
    )
    session.add(avail2)
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(sample_doctor.id, shift2.id)
    assert is_eligible is False
    assert any("Rest period" in r for r in reasons)


@pytest.mark.asyncio
async def test_consecutive_days_limit(session, sample_doctor, sample_institution, seed_lookups):
    site = sample_institution["site"]

    # Create 6 consecutive days of shifts and assign doctor
    for i in range(6):
        d = date(2026, 4, 1) + timedelta(days=i)
        shift = Shift(
            site_id=site.id, date=d,
            start_datetime=datetime(2026, 4, 1 + i, 8, 0),
            end_datetime=datetime(2026, 4, 1 + i, 14, 0),
            status=ShiftStatus.OPEN,
        )
        session.add(shift)
        await session.flush()

        session.add(ShiftAssignment(
            shift_id=shift.id, doctor_id=sample_doctor.id,
            status=AssignmentStatus.CONFIRMED, pay_amount=300.0,
        ))
        session.add(DoctorAvailability(
            doctor_id=sample_doctor.id, date=d,
            start_time=time(0, 0), end_time=time(23, 59),
        ))

    # 7th day shift
    d7 = date(2026, 4, 7)
    shift7 = Shift(
        site_id=site.id, date=d7,
        start_datetime=datetime(2026, 4, 7, 8, 0),
        end_datetime=datetime(2026, 4, 7, 14, 0),
        status=ShiftStatus.OPEN,
    )
    session.add(shift7)
    session.add(DoctorAvailability(
        doctor_id=sample_doctor.id, date=d7,
        start_time=time(0, 0), end_time=time(23, 59),
    ))
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(sample_doctor.id, shift7.id)
    assert is_eligible is False
    assert any("consecutive" in r.lower() for r in reasons)


@pytest.mark.asyncio
async def test_night_shift_limit(session, sample_doctor, sample_institution, seed_lookups):
    site = sample_institution["site"]

    # Create 8 night shifts and assign
    for i in range(8):
        d = date(2026, 4, 1) + timedelta(days=i * 3)  # Every 3 days to avoid rest/consecutive issues
        shift = Shift(
            site_id=site.id, date=d,
            start_datetime=datetime.combine(d, time(20, 0)),
            end_datetime=datetime.combine(d + timedelta(days=1), time(6, 0)),
            status=ShiftStatus.OPEN,
            is_night=True,
        )
        session.add(shift)
        await session.flush()
        session.add(ShiftAssignment(
            shift_id=shift.id, doctor_id=sample_doctor.id,
            status=AssignmentStatus.CONFIRMED, pay_amount=400.0,
        ))
        session.add(DoctorAvailability(
            doctor_id=sample_doctor.id, date=d,
            start_time=time(0, 0), end_time=time(23, 59),
        ))

    # 9th night shift
    d9 = date(2026, 4, 28)
    shift9 = Shift(
        site_id=site.id, date=d9,
        start_datetime=datetime.combine(d9, time(20, 0)),
        end_datetime=datetime.combine(d9 + timedelta(days=1), time(6, 0)),
        status=ShiftStatus.OPEN,
        is_night=True,
    )
    session.add(shift9)
    session.add(DoctorAvailability(
        doctor_id=sample_doctor.id, date=d9,
        start_time=time(0, 0), end_time=time(23, 59),
    ))
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(sample_doctor.id, shift9.id)
    assert is_eligible is False
    assert any("Night shift limit" in r for r in reasons)


@pytest.mark.asyncio
async def test_unavailability_blocks_eligibility(session, sample_doctor, sample_shift, seed_lookups):
    # Add approved unavailability
    unav = DoctorUnavailability(
        doctor_id=sample_doctor.id,
        start_date=date(2026, 3, 30),
        end_date=date(2026, 4, 5),
        reason=UnavailabilityReason.VACATION,
        is_approved=True,
    )
    session.add(unav)
    await session.flush()

    engine = EligibilityEngine(session)
    is_eligible, reasons, _ = await engine.check(sample_doctor.id, sample_shift.id)
    assert is_eligible is False
    assert any("not available" in r for r in reasons)
