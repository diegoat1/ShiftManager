"""Tests for EligibilityContext contract, builder, and check_with_context().

Coverage goals:
- EligibilityContextBuilder populates every field correctly.
- check_with_context() is synchronous and produces the same result as engine.check().
- AvailabilitySnapshot correctly distinguishes blocked-by-unavailability vs. no-slot.
- Multi-doctor bulk: one context covers several doctors simultaneously.
"""
import uuid
from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import ShiftAssignment
from app.models.availability import DoctorAvailability, DoctorUnavailability
from app.models.doctor import Doctor, DoctorCertification, DoctorLanguage
from app.models.shift import Shift, ShiftRequirement
from app.core.security import hash_password
from app.rules.eligibility import (
    AvailabilitySnapshot,
    EligibilityContextBuilder,
    EligibilityEngine,
)
from app.utils.enums import AssignmentStatus, AvailabilityType, ShiftStatus, UnavailabilityReason


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doctor(**overrides) -> Doctor:
    defaults = dict(
        fiscal_code=f"CTXT{uuid.uuid4().hex[:12].upper()}",
        first_name="Context",
        last_name="Test",
        email=f"ctx.{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("pass"),
        lat=41.9028,
        lon=12.4964,
        max_distance_km=50.0,
        is_active=True,
        years_experience=3,
        can_work_alone=True,
        can_emergency_vehicle=True,
        max_shifts_per_month=20,
    )
    defaults.update(overrides)
    return Doctor(**defaults)


async def _add_base_certs_and_lang(session, doctor, lookups):
    session.add(DoctorCertification(
        doctor_id=doctor.id,
        certification_type_id=lookups["cert_bls"].id,
        obtained_date=date(2025, 1, 1),
        expiry_date=date(2027, 1, 1),
        is_active=True,
    ))
    session.add(DoctorLanguage(
        doctor_id=doctor.id,
        language_id=lookups["lang_it"].id,
        proficiency_level=5,
    ))
    await session.flush()


def _avail(doctor_id, d=date(2026, 4, 1)):
    return DoctorAvailability(
        doctor_id=doctor_id,
        date=d,
        start_time=time(0, 0),
        end_time=time(23, 59),
        availability_type=AvailabilityType.AVAILABLE,
    )


# ---------------------------------------------------------------------------
# Parity: check() == builder + check_with_context()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parity_eligible_doctor(session, sample_doctor, sample_shift, sample_availability, seed_lookups):
    """check() and builder+check_with_context() agree: eligible doctor."""
    engine = EligibilityEngine(session)
    builder = EligibilityContextBuilder(session)

    ctx = await builder.build_for_shift(sample_shift.id, doctor_ids=[sample_doctor.id])
    eligible_ctx, reasons_ctx, _ = engine.check_with_context(sample_doctor.id, ctx)
    eligible_chk, reasons_chk, _ = await engine.check(sample_doctor.id, sample_shift.id)

    assert eligible_ctx == eligible_chk == True
    assert reasons_ctx == reasons_chk == []


@pytest.mark.asyncio
async def test_parity_inactive_doctor(session, sample_doctor, sample_shift, sample_availability, seed_lookups):
    sample_doctor.is_active = False
    await session.flush()

    engine = EligibilityEngine(session)
    builder = EligibilityContextBuilder(session)

    ctx = await builder.build_for_shift(sample_shift.id, doctor_ids=[sample_doctor.id])
    eligible_ctx, _, _ = engine.check_with_context(sample_doctor.id, ctx)
    eligible_chk, _, _ = await engine.check(sample_doctor.id, sample_shift.id)

    assert eligible_ctx == eligible_chk == False


@pytest.mark.asyncio
async def test_parity_no_availability(session, sample_doctor, sample_shift, seed_lookups):
    """No availability slot: both paths return not eligible."""
    engine = EligibilityEngine(session)
    builder = EligibilityContextBuilder(session)

    ctx = await builder.build_for_shift(sample_shift.id, doctor_ids=[sample_doctor.id])
    eligible_ctx, _, _ = engine.check_with_context(sample_doctor.id, ctx)
    eligible_chk, _, _ = await engine.check(sample_doctor.id, sample_shift.id)

    assert eligible_ctx == eligible_chk == False


@pytest.mark.asyncio
async def test_parity_missing_certification(session, sample_institution, seed_lookups):
    """Doctor missing required cert: both paths fail."""
    lookups = seed_lookups
    doctor = _doctor()
    session.add(doctor)
    await session.flush()
    # Only Italian language, no certifications
    session.add(DoctorLanguage(doctor_id=doctor.id, language_id=lookups["lang_it"].id, proficiency_level=5))
    session.add(_avail(doctor.id))

    shift = Shift(
        site_id=sample_institution["site"].id,
        date=date(2026, 4, 1),
        start_datetime=datetime(2026, 4, 1, 8, 0),
        end_datetime=datetime(2026, 4, 1, 20, 0),
        status=ShiftStatus.OPEN,
    )
    session.add(shift)
    await session.flush()
    session.add(ShiftRequirement(shift_id=shift.id, certification_type_id=lookups["cert_bls"].id, is_mandatory=True))
    await session.flush()

    engine = EligibilityEngine(session)
    builder = EligibilityContextBuilder(session)

    ctx = await builder.build_for_shift(shift.id, doctor_ids=[doctor.id])
    eligible_ctx, reasons_ctx, _ = engine.check_with_context(doctor.id, ctx)
    eligible_chk, reasons_chk, _ = await engine.check(doctor.id, shift.id)

    assert eligible_ctx == eligible_chk == False
    assert any("Missing mandatory certification" in r for r in reasons_ctx)
    assert any("Missing mandatory certification" in r for r in reasons_chk)


@pytest.mark.asyncio
async def test_parity_shift_overlap(session, sample_doctor, sample_shift, sample_institution, sample_availability, seed_lookups):
    """Overlapping assignment: both paths fail."""
    session.add(ShiftAssignment(
        shift_id=sample_shift.id, doctor_id=sample_doctor.id,
        status=AssignmentStatus.CONFIRMED, pay_amount=500.0,
    ))
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
    builder = EligibilityContextBuilder(session)

    ctx = await builder.build_for_shift(shift2.id, doctor_ids=[sample_doctor.id])
    eligible_ctx, _, _ = engine.check_with_context(sample_doctor.id, ctx)
    eligible_chk, _, _ = await engine.check(sample_doctor.id, shift2.id)

    assert eligible_ctx == eligible_chk == False


@pytest.mark.asyncio
async def test_parity_rest_period(session, sample_doctor, sample_shift, sample_institution, sample_availability, seed_lookups):
    """Rest period violation: both paths fail."""
    session.add(ShiftAssignment(
        shift_id=sample_shift.id, doctor_id=sample_doctor.id,
        status=AssignmentStatus.CONFIRMED, pay_amount=500.0,
    ))
    shift2 = Shift(
        site_id=sample_institution["site"].id,
        date=date(2026, 4, 2),
        start_datetime=datetime(2026, 4, 2, 1, 0),  # 5h gap from 20:00
        end_datetime=datetime(2026, 4, 2, 8, 0),
        status=ShiftStatus.OPEN,
    )
    session.add(shift2)
    session.add(DoctorAvailability(
        doctor_id=sample_doctor.id, date=date(2026, 4, 2),
        start_time=time(0, 0), end_time=time(23, 59),
    ))
    await session.flush()

    engine = EligibilityEngine(session)
    builder = EligibilityContextBuilder(session)

    ctx = await builder.build_for_shift(shift2.id, doctor_ids=[sample_doctor.id])
    eligible_ctx, _, _ = engine.check_with_context(sample_doctor.id, ctx)
    eligible_chk, _, _ = await engine.check(sample_doctor.id, shift2.id)

    assert eligible_ctx == eligible_chk == False


# ---------------------------------------------------------------------------
# AvailabilitySnapshot semantics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_availability_snapshot_blocked_by_unavailability(session, sample_doctor, sample_shift, seed_lookups):
    """Approved unavailability → snapshot.blocked_by_unavailability=True."""
    session.add(DoctorUnavailability(
        doctor_id=sample_doctor.id,
        start_date=date(2026, 3, 30),
        end_date=date(2026, 4, 5),
        reason=UnavailabilityReason.VACATION,
        is_approved=True,
    ))
    # Also add an availability slot — should still be blocked
    session.add(_avail(sample_doctor.id))
    await session.flush()

    builder = EligibilityContextBuilder(session)
    ctx = await builder.build_for_shift(sample_shift.id, doctor_ids=[sample_doctor.id])

    snap: AvailabilitySnapshot = ctx.availability_snapshot_by_doctor[sample_doctor.id]
    assert snap.available is False
    assert snap.blocked_by_unavailability is True


@pytest.mark.asyncio
async def test_availability_snapshot_no_slot(session, sample_doctor, sample_shift, seed_lookups):
    """No availability slot and no unavailability → snapshot shows no-slot (not blocked)."""
    builder = EligibilityContextBuilder(session)
    ctx = await builder.build_for_shift(sample_shift.id, doctor_ids=[sample_doctor.id])

    snap: AvailabilitySnapshot = ctx.availability_snapshot_by_doctor[sample_doctor.id]
    assert snap.available is False
    assert snap.blocked_by_unavailability is False
    assert snap.availability_type is None


@pytest.mark.asyncio
async def test_availability_snapshot_preferred(session, sample_doctor, sample_shift, seed_lookups):
    """PREFERRED availability slot → snapshot.availability_type=PREFERRED."""
    session.add(DoctorAvailability(
        doctor_id=sample_doctor.id,
        date=date(2026, 4, 1),
        start_time=time(0, 0),
        end_time=time(23, 59),
        availability_type=AvailabilityType.PREFERRED,
    ))
    await session.flush()

    builder = EligibilityContextBuilder(session)
    ctx = await builder.build_for_shift(sample_shift.id, doctor_ids=[sample_doctor.id])

    snap: AvailabilitySnapshot = ctx.availability_snapshot_by_doctor[sample_doctor.id]
    assert snap.available is True
    assert snap.blocked_by_unavailability is False
    assert snap.availability_type == AvailabilityType.PREFERRED


# ---------------------------------------------------------------------------
# Multi-doctor bulk context
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bulk_context_two_doctors(session, sample_institution, seed_lookups):
    """Build context for two doctors at once; one eligible, one not."""
    lookups = seed_lookups
    site = sample_institution["site"]

    # Eligible doctor
    doc_ok = _doctor()
    session.add(doc_ok)
    await session.flush()
    await _add_base_certs_and_lang(session, doc_ok, lookups)
    session.add(_avail(doc_ok.id))

    # Ineligible doctor (inactive)
    doc_inactive = _doctor(is_active=False)
    session.add(doc_inactive)
    await session.flush()
    await _add_base_certs_and_lang(session, doc_inactive, lookups)
    session.add(_avail(doc_inactive.id))

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
    builder = EligibilityContextBuilder(session)
    ctx = await builder.build_for_shift(shift.id, doctor_ids=[doc_ok.id, doc_inactive.id])

    assert doc_ok.id in ctx.doctors
    assert doc_inactive.id in ctx.doctors

    ok_elig, ok_reasons, _ = engine.check_with_context(doc_ok.id, ctx)
    bad_elig, bad_reasons, _ = engine.check_with_context(doc_inactive.id, ctx)

    assert ok_elig is True
    assert bad_elig is False
    assert any("not active" in r for r in bad_reasons)


@pytest.mark.asyncio
async def test_bulk_context_consecutive_days(session, sample_institution, seed_lookups):
    """Consecutive days count in bulk context matches single-doctor query."""
    lookups = seed_lookups
    site = sample_institution["site"]

    doctor = _doctor()
    session.add(doctor)
    await session.flush()
    await _add_base_certs_and_lang(session, doctor, lookups)

    # Assign 5 consecutive days (Apr 1-5)
    for i in range(5):
        d = date(2026, 4, 1) + timedelta(days=i)
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
        session.add(_avail(doctor.id, d=d))

    # Target: April 6 (would be 6th consecutive day)
    target_date = date(2026, 4, 6)
    target_shift = Shift(
        site_id=site.id, date=target_date,
        start_datetime=datetime.combine(target_date, time(8, 0)),
        end_datetime=datetime.combine(target_date, time(14, 0)),
        status=ShiftStatus.OPEN,
    )
    session.add(target_shift)
    session.add(_avail(doctor.id, d=target_date))
    await session.flush()

    builder = EligibilityContextBuilder(session)
    ctx = await builder.build_for_shift(target_shift.id, doctor_ids=[doctor.id])

    # Should be 6 consecutive days (5 assigned + target day)
    assert ctx.consecutive_days_by_doctor[doctor.id] == 6


@pytest.mark.asyncio
async def test_bulk_context_monthly_counts(session, sample_institution, seed_lookups):
    """Monthly shift count and night shift count in bulk context are accurate."""
    lookups = seed_lookups
    site = sample_institution["site"]

    doctor = _doctor()
    session.add(doctor)
    await session.flush()
    await _add_base_certs_and_lang(session, doctor, lookups)

    # Add 2 day shifts and 1 night shift in April
    for i in range(2):
        d = date(2026, 4, 2 + i * 5)
        s = Shift(
            site_id=site.id, date=d,
            start_datetime=datetime.combine(d, time(8, 0)),
            end_datetime=datetime.combine(d, time(14, 0)),
            status=ShiftStatus.OPEN, is_night=False,
        )
        session.add(s)
        await session.flush()
        session.add(ShiftAssignment(
            shift_id=s.id, doctor_id=doctor.id,
            status=AssignmentStatus.CONFIRMED, pay_amount=300.0,
        ))

    night_date = date(2026, 4, 15)
    night_shift = Shift(
        site_id=site.id, date=night_date,
        start_datetime=datetime.combine(night_date, time(20, 0)),
        end_datetime=datetime.combine(night_date + timedelta(days=1), time(6, 0)),
        status=ShiftStatus.OPEN, is_night=True,
    )
    session.add(night_shift)
    await session.flush()
    session.add(ShiftAssignment(
        shift_id=night_shift.id, doctor_id=doctor.id,
        status=AssignmentStatus.CONFIRMED, pay_amount=400.0,
    ))

    # Target shift later in the month
    target = date(2026, 4, 25)
    target_shift = Shift(
        site_id=site.id, date=target,
        start_datetime=datetime.combine(target, time(8, 0)),
        end_datetime=datetime.combine(target, time(14, 0)),
        status=ShiftStatus.OPEN,
    )
    session.add(target_shift)
    session.add(_avail(doctor.id, d=target))
    await session.flush()

    builder = EligibilityContextBuilder(session)
    ctx = await builder.build_for_shift(target_shift.id, doctor_ids=[doctor.id])

    assert ctx.monthly_shift_count_by_doctor[doctor.id] == 3  # 2 day + 1 night
    assert ctx.monthly_night_shift_count_by_doctor[doctor.id] == 1
