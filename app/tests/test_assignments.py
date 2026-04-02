import uuid
from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import ShiftAssignment
from app.models.availability import DoctorAvailability
from app.models.offer import ShiftOffer
from app.models.shift import Shift
from app.rules.eligibility import DoctorShiftsContextBuilder, EligibilityEngine
from app.rules.scoring import DoctorShiftsScoringContextBuilder, MatchScorer
from app.services.assignment import AssignmentService
from app.utils.enums import AssignmentStatus, AvailabilityType, OfferStatus, ShiftStatus


@pytest.mark.asyncio
async def test_check_eligibility_endpoint(client, admin_headers):
    # Setup: create doctor, institution, site, shift, availability, lookups
    ct = await client.post("/api/v1/lookups/certification-types", json={"name": "BLS", "validity_months": 24}, headers=admin_headers)
    ct_id = ct.json()["id"]
    lang = await client.post("/api/v1/lookups/languages", json={"code": "it", "name": "Italiano"}, headers=admin_headers)
    lang_id = lang.json()["id"]

    doc = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "ASN001", "first_name": "Test", "last_name": "Doc",
        "email": "asn1@test.com", "password": "pass", "lat": 41.9, "lon": 12.5,
    }, headers=admin_headers)
    doc_id = doc.json()["id"]

    await client.post(f"/api/v1/doctors/{doc_id}/certifications", json={
        "certification_type_id": ct_id, "obtained_date": "2025-01-01", "expiry_date": "2027-01-01",
    }, headers=admin_headers)
    await client.post(f"/api/v1/doctors/{doc_id}/languages", json={
        "language_id": lang_id, "proficiency_level": 5,
    }, headers=admin_headers)

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Ospedale", "tax_code": "ASN001",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS", "lat": 41.88, "lon": 12.47,
    }, headers=admin_headers)
    site_id = site.json()["id"]

    shift = await client.post("/api/v1/shifts/", json={
        "site_id": site_id,
        "date": "2026-04-01",
        "start_datetime": "2026-04-01T08:00:00",
        "end_datetime": "2026-04-01T20:00:00",
    }, headers=admin_headers)
    shift_id = shift.json()["id"]

    # Add requirements to shift
    await client.post(f"/api/v1/shifts/{shift_id}/requirements", json={
        "certification_type_id": ct_id, "is_mandatory": True,
    }, headers=admin_headers)
    await client.post(f"/api/v1/shifts/{shift_id}/language-requirements", json={
        "language_id": lang_id, "min_proficiency": 3,
    }, headers=admin_headers)

    # Set availability
    await client.post(f"/api/v1/doctors/{doc_id}/availability", json={
        "date": "2026-04-01", "start_time": "00:00:00", "end_time": "23:59:00",
    }, headers=admin_headers)

    # Check eligibility
    resp = await client.get(f"/api/v1/assignments/check/{doc_id}/{shift_id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_eligible"] is True


@pytest.mark.asyncio
async def test_assign_and_unassign(client, admin_headers):
    # Setup minimal
    doc = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "ASN002", "first_name": "T", "last_name": "D",
        "email": "asn2@test.com", "password": "pass", "lat": 41.9, "lon": 12.5,
    }, headers=admin_headers)
    doc_id = doc.json()["id"]

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "ASN002",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS", "lat": 41.9, "lon": 12.5,
    }, headers=admin_headers)
    site_id = site.json()["id"]

    shift = await client.post("/api/v1/shifts/", json={
        "site_id": site_id,
        "date": "2026-04-01",
        "start_datetime": "2026-04-01T08:00:00",
        "end_datetime": "2026-04-01T20:00:00",
    }, headers=admin_headers)
    shift_id = shift.json()["id"]

    await client.post(f"/api/v1/doctors/{doc_id}/availability", json={
        "date": "2026-04-01", "start_time": "00:00:00", "end_time": "23:59:00",
    }, headers=admin_headers)

    # Assign
    resp = await client.post("/api/v1/assignments/", json={
        "shift_id": shift_id, "doctor_id": doc_id,
    }, headers=admin_headers)
    assert resp.status_code == 201
    assignment_id = resp.json()["id"]

    # List shift assignments
    resp = await client.get(f"/api/v1/assignments/shift/{shift_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # Unassign
    resp = await client.delete(f"/api/v1/assignments/{assignment_id}", headers=admin_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_assign_ineligible_doctor(client, admin_headers):
    doc = await client.post("/api/v1/doctors/", json={
        "fiscal_code": "ASN003", "first_name": "T", "last_name": "D",
        "email": "asn3@test.com", "password": "pass",
    }, headers=admin_headers)
    doc_id = doc.json()["id"]

    inst = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "ASN003",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={"name": "PS"}, headers=admin_headers)
    site_id = site.json()["id"]

    shift = await client.post("/api/v1/shifts/", json={
        "site_id": site_id,
        "date": "2026-04-01",
        "start_datetime": "2026-04-01T08:00:00",
        "end_datetime": "2026-04-01T20:00:00",
    }, headers=admin_headers)
    shift_id = shift.json()["id"]

    # No availability set — should fail
    resp = await client.post("/api/v1/assignments/", json={
        "shift_id": shift_id, "doctor_id": doc_id,
    }, headers=admin_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_eligible_doctors(client, admin_headers):
    inst = await client.post("/api/v1/institutions/", json={
        "name": "Osp", "tax_code": "ASN004",
    }, headers=admin_headers)
    inst_id = inst.json()["id"]
    site = await client.post(f"/api/v1/institutions/{inst_id}/sites", json={
        "name": "PS", "lat": 41.9, "lon": 12.5,
    }, headers=admin_headers)
    site_id = site.json()["id"]

    shift = await client.post("/api/v1/shifts/", json={
        "site_id": site_id,
        "date": "2026-04-01",
        "start_datetime": "2026-04-01T08:00:00",
        "end_datetime": "2026-04-01T20:00:00",
    }, headers=admin_headers)
    shift_id = shift.json()["id"]

    resp = await client.get(f"/api/v1/assignments/eligible/{shift_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_eligible_doctors_shift_not_found(client, admin_headers):
    """GET /eligible/{shift_id} returns 404 when shift doesn't exist."""
    bad_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/assignments/eligible/{bad_id}", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_eligible_doctors_bulk_result(
    session, sample_doctor, sample_shift, sample_availability, seed_lookups
):
    """get_eligible_doctors() returns the eligible doctor at the top via bulk context."""
    svc = AssignmentService(session)
    results = await svc.get_eligible_doctors(sample_shift.id)

    assert isinstance(results, list)
    assert len(results) > 0
    # Eligible doctors come first, sample_doctor should be in the eligible group
    eligible = [r for r in results if r["eligibility"].is_eligible]
    assert any(r["doctor_id"] == sample_doctor.id for r in eligible)
    # Eligible entries get a rank assigned
    for i, entry in enumerate(eligible):
        assert entry["rank"] == i + 1


# ---------------------------------------------------------------------------
# PR 6a: bulk assignment + offer lookup semantics
# ---------------------------------------------------------------------------

async def _make_open_shift(session, site_id, shift_date=date(2026, 5, 1)):
    """Helper: create an OPEN shift on the given date."""
    s = Shift(
        site_id=site_id,
        date=shift_date,
        start_datetime=datetime.combine(shift_date, time(8, 0)),
        end_datetime=datetime.combine(shift_date, time(20, 0)),
        status=ShiftStatus.OPEN,
    )
    session.add(s)
    await session.flush()
    return s


@pytest.mark.asyncio
async def test_already_applied_preserves_semantics_with_cancelled_assignment(
    session, sample_doctor, sample_institution, seed_lookups
):
    """already_applied=True even for CANCELLED assignments — preserving get_existing() semantics."""
    site = sample_institution["site"]
    shift_a = await _make_open_shift(session, site.id, date(2026, 5, 1))
    shift_b = await _make_open_shift(session, site.id, date(2026, 5, 10))

    # CANCELLED assignment on shift_a
    session.add(ShiftAssignment(
        shift_id=shift_a.id,
        doctor_id=sample_doctor.id,
        status=AssignmentStatus.CANCELLED,
        pay_amount=0.0,
    ))
    # Availability on both dates
    for d in [date(2026, 5, 1), date(2026, 5, 10)]:
        session.add(DoctorAvailability(
            doctor_id=sample_doctor.id, date=d,
            start_time=time(0, 0), end_time=time(23, 59),
            availability_type=AvailabilityType.AVAILABLE,
        ))
    await session.flush()

    svc = AssignmentService(session)
    results = await svc.get_available_shifts_for_doctor(
        sample_doctor.id,
        start=date(2026, 5, 1),
        end=date(2026, 5, 31),
    )

    by_shift = {r["id"]: r for r in results}
    assert by_shift[shift_a.id]["already_applied"] is True   # CANCELLED still counts
    assert by_shift[shift_b.id]["already_applied"] is False


@pytest.mark.asyncio
async def test_has_pending_offer_only_for_active_offers(
    session, sample_doctor, sample_institution, seed_lookups
):
    """has_pending_offer=True only for PROPOSED|VIEWED offers, not REJECTED."""
    from datetime import timezone
    site = sample_institution["site"]
    shift_a = await _make_open_shift(session, site.id, date(2026, 5, 1))
    shift_b = await _make_open_shift(session, site.id, date(2026, 5, 10))

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # PROPOSED offer on shift_a
    session.add(ShiftOffer(
        shift_id=shift_a.id, doctor_id=sample_doctor.id,
        status=OfferStatus.PROPOSED,
        offered_at=now,
        expires_at=now + timedelta(hours=12),
    ))
    # REJECTED offer on shift_b
    session.add(ShiftOffer(
        shift_id=shift_b.id, doctor_id=sample_doctor.id,
        status=OfferStatus.REJECTED,
        offered_at=now,
        expires_at=now + timedelta(hours=12),
    ))
    for d in [date(2026, 5, 1), date(2026, 5, 10)]:
        session.add(DoctorAvailability(
            doctor_id=sample_doctor.id, date=d,
            start_time=time(0, 0), end_time=time(23, 59),
            availability_type=AvailabilityType.AVAILABLE,
        ))
    await session.flush()

    svc = AssignmentService(session)
    results = await svc.get_available_shifts_for_doctor(
        sample_doctor.id,
        start=date(2026, 5, 1),
        end=date(2026, 5, 31),
    )

    by_shift = {r["id"]: r for r in results}
    assert by_shift[shift_a.id]["has_pending_offer"] is True   # PROPOSED
    assert by_shift[shift_b.id]["has_pending_offer"] is False  # REJECTED doesn't count


# ---------------------------------------------------------------------------
# PR 6b: DoctorShiftsContextBuilder parity test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_doctor_shifts_context_builder_parity(
    session, sample_doctor, sample_shift, sample_availability, seed_lookups
):
    """check_with_context() via DoctorShiftsContextBuilder agrees with check() for same shift."""
    engine = EligibilityEngine(session)

    # Direct path: check() fires per-shift queries
    direct_eligible, direct_reasons, _ = await engine.check(sample_doctor.id, sample_shift.id)

    # Bulk path: builder + check_with_context()
    ctx_by_shift = await DoctorShiftsContextBuilder(session).build(
        sample_doctor.id, [sample_shift]
    )
    assert sample_shift.id in ctx_by_shift
    ctx = ctx_by_shift[sample_shift.id]
    bulk_eligible, bulk_reasons, _ = engine.check_with_context(sample_doctor.id, ctx)

    assert bulk_eligible == direct_eligible, (
        f"Parity mismatch: direct={direct_reasons}, bulk={bulk_reasons}"
    )


@pytest.mark.asyncio
async def test_doctor_shifts_context_builder_empty_shifts(session, sample_doctor):
    """build() with an empty shift list returns an empty dict."""
    result = await DoctorShiftsContextBuilder(session).build(sample_doctor.id, [])
    assert result == {}


@pytest.mark.asyncio
async def test_doctor_shifts_context_builder_unknown_doctor(session, sample_shift):
    """build() raises ValueError when doctor does not exist."""
    import pytest
    with pytest.raises(ValueError, match="not found"):
        await DoctorShiftsContextBuilder(session).build(uuid.uuid4(), [sample_shift])


# ---------------------------------------------------------------------------
# PR 6c1: DoctorShiftsScoringContext parity + semantics tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scoring_parity_score_vs_score_with_context(
    session, sample_doctor, sample_shift, sample_availability, seed_lookups
):
    """score_with_context() agrees with score() for the same doctor+shift."""
    from app.repositories.doctor import DoctorRepository
    from app.repositories.shift import ShiftRepository

    # Reload shift with eagerly-loaded relations (score_with_context is sync)
    shift = await ShiftRepository(session).get_with_requirements(sample_shift.id)
    scorer = MatchScorer(session)

    # Direct path
    direct = await scorer.score(sample_doctor.id, shift)

    # Bulk path
    doctor = await DoctorRepository(session).get_with_relations(sample_doctor.id)
    ctx = await DoctorShiftsScoringContextBuilder(session).build(
        doctor=doctor, shifts=[shift],
    )
    bulk = scorer.score_with_context(shift, ctx)

    assert bulk.score == direct.score, (
        f"Score parity mismatch: direct={direct.breakdown.to_dict()}, "
        f"bulk={bulk.breakdown.to_dict()}"
    )
    assert bulk.breakdown.to_dict() == direct.breakdown.to_dict()


@pytest.mark.asyncio
async def test_scoring_availability_with_unavailability_preserves_raw_type(
    session, sample_doctor, sample_shift, sample_availability, seed_lookups
):
    """Scoring uses raw availability type — approved unavailability does NOT zero out the score.

    This tests the deliberate semantic split: eligibility checks unavailability,
    scoring only looks at the availability slot.
    """
    from app.models.availability import DoctorUnavailability
    from app.repositories.shift import ShiftRepository

    # Add an approved unavailability covering the shift date
    session.add(DoctorUnavailability(
        doctor_id=sample_doctor.id,
        start_date=sample_shift.date,
        end_date=sample_shift.date,
        is_approved=True,
        reason="test",
    ))
    await session.flush()

    # Reload shift with relations (score_with_context is sync)
    shift = await ShiftRepository(session).get_with_requirements(sample_shift.id)
    scorer = MatchScorer(session)
    result = await scorer.score(sample_doctor.id, shift)

    # Despite approved unavailability, the raw availability slot still scores > 0
    assert result.breakdown.availability > 0, (
        "Scoring should use raw availability type, not be blocked by unavailability"
    )


@pytest.mark.asyncio
async def test_scoring_site_affinity_includes_cancelled_assignments(
    session, sample_doctor, sample_institution, seed_lookups
):
    """CANCELLED assignments still contribute to site affinity (preserves get_doctor_shifts semantics)."""
    from app.repositories.shift import ShiftRepository

    site = sample_institution["site"]
    shift = await _make_open_shift(session, site.id, date(2026, 5, 1))

    # CANCELLED assignment on the same site — should still count for affinity
    session.add(ShiftAssignment(
        shift_id=shift.id,
        doctor_id=sample_doctor.id,
        status=AssignmentStatus.CANCELLED,
        pay_amount=0.0,
    ))
    # Availability so scoring doesn't get 0 for availability
    session.add(DoctorAvailability(
        doctor_id=sample_doctor.id, date=date(2026, 5, 1),
        start_time=time(0, 0), end_time=time(23, 59),
        availability_type=AvailabilityType.AVAILABLE,
    ))
    await session.flush()

    # Reload with relations for sync score_with_context
    shift = await ShiftRepository(session).get_with_requirements(shift.id)
    scorer = MatchScorer(session)
    result = await scorer.score(sample_doctor.id, shift)

    # Site affinity should be 15 (worked at same site recently via CANCELLED assignment)
    assert result.breakdown.site_affinity == 15, (
        f"CANCELLED assignment should count for site affinity, got {result.breakdown.site_affinity}"
    )


# ---------------------------------------------------------------------------
# PR 6c2: score_many_with_eligibility_context parity test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_score_many_with_eligibility_context_parity(
    session, sample_doctor, sample_shift, sample_availability, seed_lookups
):
    """score_many_with_eligibility_context() agrees with score_many() for the same inputs."""
    from app.rules.eligibility import EligibilityContextBuilder

    # Build eligibility context (same as get_eligible_doctors does)
    ctx = await EligibilityContextBuilder(session).build_for_shift(
        sample_shift.id, doctor_ids=[sample_doctor.id]
    )
    shift = ctx.shift

    scorer = MatchScorer(session)

    # Direct path: score_many (N+1 queries)
    direct = await scorer.score_many([sample_doctor.id], shift)

    # Bulk path: score_many_with_eligibility_context (2 queries)
    bulk = await scorer.score_many_with_eligibility_context(
        [sample_doctor.id], shift, ctx
    )

    assert len(direct) == len(bulk) == 1
    assert direct[0].score == bulk[0].score, (
        f"Score parity mismatch: direct={direct[0].breakdown.to_dict()}, "
        f"bulk={bulk[0].breakdown.to_dict()}"
    )
    assert direct[0].breakdown.to_dict() == bulk[0].breakdown.to_dict()
