"""Generate realistic test data for integral platform evaluation.

Creates (idempotent – skips if doctors > 10 already exist):
  Institutions:
    - PS Palmanova site under ASU FC (all codes, 2 medici per turno)
    - SUEM 118 BL – PPI Auronzo di Cadore (ACLS+BLSD mandatory, 118 uscita, all codes)
    - Guardia Medica Carnia – Tolmezzo (weekday nights + weekend days, no special certs)
  Doctors:
    - 50 doctors with user accounts (email: nome.cognome.N@medici.test, pwd: Medico2026!)
    - Varied certifications, code levels, experience, preferences
  Shifts:
    - April + May 2026 for all 3 institutions
  Assignments:
    - ~30% of shifts assigned by coordinator (CONFIRMED)
    - ~70% left OPEN for doctors to claim

Usage: python -m app.utils.generate_test_data
"""
import asyncio
import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.assignment import ShiftAssignment
from app.models.availability import DoctorAvailability
from app.models.doctor import (
    CertificationType,
    Doctor,
    DoctorCertification,
    DoctorLanguage,
    DoctorPreference,
    Language,
)
from app.models.institution import Institution, InstitutionSite
from app.models.requirement import CodeLevel, InstitutionLanguageRequirement, InstitutionRequirement
from app.models.shift import Shift
from app.models.user import User
from app.utils.enums import AssignmentStatus, AvailabilityType, HomologationStatus, UserRole
from app.utils.seed import seed

random.seed(2026)

DOCTOR_PASSWORD = hash_password("Medico2026!")

# ── Italian names ──────────────────────────────────────────────────────────────

FIRST_M = ["Marco", "Luca", "Alessandro", "Andrea", "Francesco", "Matteo",
           "Lorenzo", "Davide", "Stefano", "Simone", "Fabio", "Antonio",
           "Giovanni", "Roberto", "Paolo", "Massimo", "Enrico", "Federico",
           "Claudio", "Giorgio", "Daniele", "Michele", "Nicola", "Filippo", "Emanuele"]

FIRST_F = ["Maria", "Giulia", "Francesca", "Sara", "Valentina", "Chiara", "Laura",
           "Elena", "Alessandra", "Silvia", "Federica", "Anna", "Martina", "Paola",
           "Roberta", "Monica", "Cristina", "Barbara", "Elisa", "Ilaria",
           "Serena", "Marta", "Veronica", "Claudia", "Raffaella"]

LAST = ["Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo",
        "Ricci", "Marino", "Greco", "Bruno", "Gallo", "Conti", "De Luca",
        "Mancini", "Costa", "Giordano", "Mazza", "Rizzo", "Lombardi",
        "Moretti", "Barbieri", "Fontana", "Santoro", "Mariani",
        "Pellegrini", "Caruso", "Ferraro", "Gentile", "Monti"]

# Cities near Friuli-Venezia Giulia / Veneto
CITIES = [
    {"name": "Udine",       "province": "UD", "lat": 46.0711, "lon": 13.2350},
    {"name": "Pordenone",   "province": "PN", "lat": 45.9564, "lon": 12.6613},
    {"name": "Gorizia",     "province": "GO", "lat": 45.9408, "lon": 13.6213},
    {"name": "Trieste",     "province": "TS", "lat": 45.6495, "lon": 13.7768},
    {"name": "Venezia",     "province": "VE", "lat": 45.4408, "lon": 12.3155},
    {"name": "Belluno",     "province": "BL", "lat": 46.1410, "lon": 12.2158},
    {"name": "Treviso",     "province": "TV", "lat": 45.6669, "lon": 12.2430},
    {"name": "Tolmezzo",    "province": "UD", "lat": 46.4022, "lon": 13.0139},
    {"name": "Lignano",     "province": "UD", "lat": 45.6869, "lon": 13.1285},
    {"name": "Palmanova",   "province": "UD", "lat": 45.9019, "lon": 13.3117},
]


def _fake_fiscal(i: int) -> str:
    alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    consonants = "BCDFGHJKLMNPQRSTVWXYZ"
    base = f"{''.join(random.choices(alpha, k=6))}{random.randint(60,99)}"
    base += "ABCDEHLMPRST"[i % 12]
    base += f"{random.randint(1,28):02d}H{random.randint(100,999)}"
    base += alpha[(i * 7) % 26]
    return base[:16]


# ── Institution builders ───────────────────────────────────────────────────────

async def _get_or_create_institution(session, tax_code: str, **kwargs) -> Institution:
    res = await session.execute(select(Institution).where(Institution.tax_code == tax_code))
    existing = res.scalar_one_or_none()
    if existing:
        return existing
    inst = Institution(tax_code=tax_code, **kwargs)
    session.add(inst)
    await session.flush()
    return inst


async def create_institutions(session, code_level_map: dict, cert_map: dict, lang_map: dict):
    """Create/update test institutions and return list of (site, institution_type_str) tuples."""
    sites = []

    # ── 1. PS Palmanova site under ASU FC ─────────────────────────────────────
    asufc_res = await session.execute(
        select(Institution).where(Institution.tax_code == "02985660303")
    )
    asufc = asufc_res.scalar_one_or_none()
    if asufc:
        palm_site_res = await session.execute(
            select(InstitutionSite).where(
                InstitutionSite.institution_id == asufc.id,
                InstitutionSite.name.contains("Palmanova"),
            )
        )
        if not palm_site_res.scalar_one_or_none():
            site = InstitutionSite(
                institution_id=asufc.id,
                name="Presidio Ospedaliero di Palmanova - Pronto Soccorso",
                address="Via Natisone, 1",
                city="Palmanova",
                province="UD",
                lat=45.9019,
                lon=13.3117,
                min_code_level_id=code_level_map.get("RED"),
                requires_independent_work=False,
                requires_emergency_vehicle=False,
                min_years_experience=2,
                lodging_available=False,
                meal_support=True,
                parking_available=True,
            )
            session.add(site)
            await session.flush()
            sites.append((site, "pronto_soccorso"))
            print("  → PS Palmanova site created under ASU FC")
        else:
            sites.append((palm_site_res.scalar_one_or_none(), "pronto_soccorso"))

    # ── 2. SUEM 118 BL – PPI Auronzo di Cadore ────────────────────────────────
    suem = await _get_or_create_institution(
        session,
        tax_code="00414010254",
        name="SUEM 118 – Azienda ULSS 1 Dolomiti",
        address="Via Feltre, 57",
        city="Belluno",
        province="BL",
        institution_type="punto_primo_intervento",
    )
    auronzo_res = await session.execute(
        select(InstitutionSite).where(
            InstitutionSite.institution_id == suem.id,
            InstitutionSite.name.contains("Auronzo"),
        )
    )
    if not auronzo_res.scalar_one_or_none():
        site_auronzo = InstitutionSite(
            institution_id=suem.id,
            name="Postazione 118 – Auronzo di Cadore",
            address="Via Roma, 30",
            city="Auronzo di Cadore",
            province="BL",
            lat=46.5580,
            lon=12.4346,
            min_code_level_id=None,           # all codes
            requires_independent_work=True,
            requires_emergency_vehicle=True,  # uscita 118
            min_years_experience=1,
            lodging_available=True,
            meal_support=False,
            parking_available=True,
        )
        session.add(site_auronzo)
        await session.flush()

        # Cert requirements: ACLS + BLSD mandatory
        for cert_name in ["ACLS", "BLSD"]:
            ct = cert_map.get(cert_name)
            if ct:
                res = await session.execute(
                    select(InstitutionRequirement).where(
                        InstitutionRequirement.institution_id == suem.id,
                        InstitutionRequirement.certification_type_id == ct.id,
                    )
                )
                if not res.scalar_one_or_none():
                    session.add(InstitutionRequirement(
                        institution_id=suem.id,
                        certification_type_id=ct.id,
                        is_mandatory=True,
                    ))
        await session.flush()
        sites.append((site_auronzo, "punto_primo_intervento"))
        print("  → PPI Auronzo di Cadore created under SUEM 118")
    else:
        sites.append((auronzo_res.scalar_one_or_none(), "punto_primo_intervento"))

    # ── 3. Guardia Medica Carnia ───────────────────────────────────────────────
    gmc = await _get_or_create_institution(
        session,
        tax_code="09387550018",
        name="Guardia Medica Carnia – ASUFC",
        address="Via della Vittoria, 10",
        city="Tolmezzo",
        province="UD",
        institution_type="guardia_medica",
    )
    gmc_site_res = await session.execute(
        select(InstitutionSite).where(InstitutionSite.institution_id == gmc.id)
    )
    if not gmc_site_res.scalar_one_or_none():
        site_gmc = InstitutionSite(
            institution_id=gmc.id,
            name="GM Carnia – Distretto Tolmezzo",
            address="Via della Vittoria, 10",
            city="Tolmezzo",
            province="UD",
            lat=46.4022,
            lon=13.0139,
            min_code_level_id=code_level_map.get("GREEN"),
            requires_independent_work=True,
            requires_emergency_vehicle=False,
            min_years_experience=0,
            lodging_available=False,
            meal_support=False,
            parking_available=True,
        )
        session.add(site_gmc)
        await session.flush()

        # Italian language requirement: A1/A2 minimum
        it_lang = lang_map.get("it")
        if it_lang:
            session.add(InstitutionLanguageRequirement(
                institution_id=gmc.id,
                language_id=it_lang.id,
                min_proficiency=1,
            ))
        await session.flush()
        sites.append((site_gmc, "guardia_medica"))
        print("  → Guardia Medica Carnia created")
    else:
        sites.append((gmc_site_res.scalar_one_or_none(), "guardia_medica"))

    return sites


# ── Doctor builder ─────────────────────────────────────────────────────────────

async def create_doctors(session, cert_map, lang_map, code_level_map, n=50):
    """Create n doctors with varied profiles and linked user accounts."""
    first_names = FIRST_M + FIRST_F
    doctors = []

    # Distribution profiles
    profiles = []
    # Group A (15): Basic – BLSD only, white/green codes, 0-3y exp
    for _ in range(15):
        profiles.append({"certs": ["BLSD"], "max_cl": "GREEN", "vehicle": False, "alone": False, "exp_range": (0, 3)})
    # Group B (15): Standard – BLSD+ACLS, green/yellow, 3-8y exp
    for _ in range(15):
        profiles.append({"certs": ["BLSD", "ACLS"], "max_cl": "YELLOW", "vehicle": False, "alone": True, "exp_range": (3, 8)})
    # Group C (10): Advanced – BLSD+ACLS+PALS, yellow/orange, 5-15y exp
    for _ in range(10):
        profiles.append({"certs": ["BLSD", "ACLS", "PALS"], "max_cl": "ORANGE", "vehicle": False, "alone": True, "exp_range": (5, 15)})
    # Group D (5): 118-ready – BLSD+ACLS, red code, vehicle, 4-12y exp
    for _ in range(5):
        profiles.append({"certs": ["BLSD", "ACLS"], "max_cl": "RED", "vehicle": True, "alone": True, "exp_range": (4, 12)})
    # Group E (5): Expert – BLSD+ACLS+PTC+ATLS, red, vehicle, 10-25y
    for _ in range(5):
        profiles.append({"certs": ["BLSD", "ACLS", "PTC", "ATLS"], "max_cl": "RED", "vehicle": True, "alone": True, "exp_range": (10, 25)})

    random.shuffle(profiles)

    for i, profile in enumerate(profiles[:n]):
        fname = first_names[i % len(first_names)]
        lname = LAST[i % len(LAST)]
        city = CITIES[i % len(CITIES)]
        exp = random.randint(*profile["exp_range"])
        email = f"{fname.lower()}.{lname.lower().replace(' ', '')}.{i}@medici.test"

        # User account
        user_res = await session.execute(select(User).where(User.email == email))
        user = user_res.scalar_one_or_none()
        if not user:
            user = User(email=email, password_hash=DOCTOR_PASSWORD, role=UserRole.MEDICO)
            session.add(user)
            await session.flush()

        # Doctor record
        doc_res = await session.execute(select(Doctor).where(Doctor.email == email))
        existing_doc = doc_res.scalar_one_or_none()
        if existing_doc:
            doctors.append(existing_doc)
            continue

        max_cl_id = code_level_map.get(profile["max_cl"])

        doc = Doctor(
            user_id=user.id,
            fiscal_code=_fake_fiscal(i),
            first_name=fname,
            last_name=lname,
            email=email,
            password_hash=DOCTOR_PASSWORD,
            phone=f"+39 {random.randint(320,399)} {random.randint(1000000,9999999)}",
            lat=city["lat"] + random.uniform(-0.2, 0.2),
            lon=city["lon"] + random.uniform(-0.2, 0.2),
            max_distance_km=random.choice([50, 80, 100, 150, 200]),
            willing_to_relocate=random.random() < 0.3,
            willing_overnight_stay=random.random() < 0.4,
            max_shifts_per_month=random.choice([8, 10, 12, 15, 20]),
            max_night_shifts_per_month=random.choice([None, 4, 6, 8]),
            max_code_level_id=max_cl_id,
            can_work_alone=profile["alone"],
            can_emergency_vehicle=profile["vehicle"],
            years_experience=exp,
            is_active=True,
            homologation_status=HomologationStatus.APPROVED,
            ordine_province=city["province"],
            ordine_number=f"{random.randint(1000,9999)}",
            has_own_vehicle=True,
            domicile_city=city["name"],
            profile_completion_percent=random.randint(60, 95),
        )
        session.add(doc)
        await session.flush()

        # Certifications
        for cert_name in profile["certs"]:
            ct = cert_map.get(cert_name)
            if not ct:
                continue
            obtained = date.today() - timedelta(days=random.randint(180, exp * 300 + 365))
            expiry = obtained + timedelta(days=ct.validity_months * 30) if ct.validity_months else None
            session.add(DoctorCertification(
                doctor_id=doc.id,
                certification_type_id=ct.id,
                obtained_date=obtained,
                expiry_date=expiry,
                is_active=True if not expiry or expiry > date.today() else False,
            ))

        # Languages
        it = lang_map.get("it")
        if it:
            session.add(DoctorLanguage(doctor_id=doc.id, language_id=it.id, proficiency_level=5))
        if random.random() < 0.5:
            en = lang_map.get("en")
            if en:
                session.add(DoctorLanguage(doctor_id=doc.id, language_id=en.id, proficiency_level=random.choice([2, 3, 4])))
        if random.random() < 0.2:
            de = lang_map.get("de")
            if de:
                session.add(DoctorLanguage(doctor_id=doc.id, language_id=de.id, proficiency_level=random.choice([2, 3])))

        # Preferences
        session.add(DoctorPreference(
            doctor_id=doc.id,
            prefers_day=random.random() < 0.6,
            prefers_night=random.random() < 0.35,
            prefers_weekends=random.random() < 0.2,
            avoids_weekends=random.random() < 0.3,
            min_pay_per_shift=random.choice([None, 300, 400, 500, 600]),
            max_preferred_distance_km=random.choice([None, 50, 80, 120]),
        ))

        doctors.append(doc)
        if (i + 1) % 10 == 0:
            await session.flush()

    await session.flush()
    return doctors


# ── Shift builder ──────────────────────────────────────────────────────────────

SHIFT_CONFIGS = {
    "pronto_soccorso": [
        {"start": time(7, 0),  "end": time(19, 0), "is_night": False, "pay": 650, "docs": 2, "type": "day"},
        {"start": time(19, 0), "end": time(7, 0),  "is_night": True,  "pay": 850, "docs": 2, "type": "night"},
    ],
    "punto_primo_intervento": [
        {"start": time(8, 0),  "end": time(20, 0), "is_night": False, "pay": 500, "docs": 1, "type": "day"},
        {"start": time(20, 0), "end": time(8, 0),  "is_night": True,  "pay": 650, "docs": 1, "type": "night"},
    ],
    "guardia_medica": [
        {"start": time(20, 0), "end": time(8, 0),  "is_night": True,  "pay": 380, "docs": 1, "type": "night",       "weekday_only": True},
        {"start": time(8, 0),  "end": time(20, 0), "is_night": False, "pay": 350, "docs": 1, "type": "weekend_day", "weekend_only": True},
    ],
}


async def create_shifts(session, sites_with_type: list, months: list[date], code_level_map: dict):
    shifts = []
    for target_month in months:
        first = target_month.replace(day=1)
        if first.month == 12:
            last = first.replace(year=first.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last = first.replace(month=first.month + 1, day=1) - timedelta(days=1)

        for site, inst_type in sites_with_type:
            templates = SHIFT_CONFIGS.get(inst_type, [])
            current = first
            while current <= last:
                is_weekend = current.weekday() >= 5
                for tmpl in templates:
                    if tmpl.get("weekday_only") and is_weekend:
                        continue
                    if tmpl.get("weekend_only") and not is_weekend:
                        continue

                    start_dt = datetime.combine(current, tmpl["start"])
                    end_dt = datetime.combine(current, tmpl["end"])
                    if tmpl["end"] <= tmpl["start"]:
                        end_dt += timedelta(days=1)

                    # Check if shift already exists
                    existing = await session.execute(
                        select(Shift).where(
                            Shift.site_id == site.id,
                            Shift.start_datetime == start_dt,
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    shift = Shift(
                        site_id=site.id,
                        date=current,
                        start_datetime=start_dt,
                        end_datetime=end_dt,
                        required_doctors=tmpl["docs"],
                        status="open",
                        base_pay=tmpl["pay"],
                        is_night=tmpl["is_night"],
                        shift_type=tmpl["type"],
                        priority=2 if inst_type == "pronto_soccorso" else 3,
                        min_code_level_id=site.min_code_level_id,
                        requires_independent_work=site.requires_independent_work,
                        requires_emergency_vehicle=site.requires_emergency_vehicle,
                        min_years_experience=site.min_years_experience,
                    )
                    session.add(shift)
                    shifts.append(shift)
                current += timedelta(days=1)
        await session.flush()
    return shifts


# ── Availability builder ───────────────────────────────────────────────────────

async def create_availability(session, doctors: list, months: list[date]):
    for target_month in months:
        first = target_month.replace(day=1)
        if first.month == 12:
            last = first.replace(year=first.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            last = first.replace(month=first.month + 1, day=1) - timedelta(days=1)

        count = 0
        for doc in doctors:
            current = first
            while current <= last:
                if random.random() < 0.75:
                    if random.random() < 0.8:
                        # Check existing
                        ex = await session.execute(
                            select(DoctorAvailability).where(
                                DoctorAvailability.doctor_id == doc.id,
                                DoctorAvailability.date == current,
                                DoctorAvailability.start_time == time(7, 0),
                            )
                        )
                        if not ex.scalar_one_or_none():
                            session.add(DoctorAvailability(
                                doctor_id=doc.id,
                                date=current,
                                start_time=time(7, 0),
                                end_time=time(20, 0),
                                availability_type=AvailabilityType.AVAILABLE,
                            ))
                            count += 1

                    if random.random() < 0.4:
                        ex = await session.execute(
                            select(DoctorAvailability).where(
                                DoctorAvailability.doctor_id == doc.id,
                                DoctorAvailability.date == current,
                                DoctorAvailability.start_time == time(19, 0),
                            )
                        )
                        if not ex.scalar_one_or_none():
                            session.add(DoctorAvailability(
                                doctor_id=doc.id,
                                date=current,
                                start_time=time(19, 0),
                                end_time=time(23, 59),
                                availability_type=AvailabilityType.AVAILABLE,
                            ))
                            count += 1

                current += timedelta(days=1)

            if count > 300:
                await session.flush()
                count = 0

    await session.flush()


# ── Assignment builder ─────────────────────────────────────────────────────────

def _doctor_eligible(doc: Doctor, shift: Shift, cert_ids: set) -> bool:
    """Check basic eligibility: vehicle, alone, code level, certs."""
    if shift.requires_emergency_vehicle and not doc.can_emergency_vehicle:
        return False
    if shift.requires_independent_work and not doc.can_work_alone:
        return False
    if shift.min_years_experience and doc.years_experience < shift.min_years_experience:
        return False
    if shift.min_code_level_id and doc.max_code_level_id:
        if doc.max_code_level_id < shift.min_code_level_id:
            return False
    return True


async def create_assignments(session, shifts: list, doctors: list):
    """Assign ~30% of shifts via coordinator (CONFIRMED). Update shift status."""
    # Preload doctor cert ids
    doc_cert_ids: dict = {}
    for doc in doctors:
        res = await session.execute(
            select(DoctorCertification.certification_type_id).where(
                DoctorCertification.doctor_id == doc.id,
                DoctorCertification.is_active == True,
            )
        )
        doc_cert_ids[doc.id] = {row[0] for row in res.all()}

    assigned_count = 0
    # Only assign shifts in April (leave May mostly open for live testing)
    april_shifts = [s for s in shifts if s.date.month == 4]
    target = int(len(april_shifts) * 0.30)
    candidates = random.sample(april_shifts, min(target, len(april_shifts)))

    for shift in candidates:
        needed = shift.required_doctors
        eligible = [
            d for d in doctors
            if _doctor_eligible(d, shift, doc_cert_ids.get(d.id, set()))
        ]
        if not eligible:
            continue

        assigned = 0
        random.shuffle(eligible)
        for doc in eligible:
            if assigned >= needed:
                break
            # Check no duplicate
            ex = await session.execute(
                select(ShiftAssignment).where(
                    ShiftAssignment.shift_id == shift.id,
                    ShiftAssignment.doctor_id == doc.id,
                )
            )
            if ex.scalar_one_or_none():
                continue

            session.add(ShiftAssignment(
                shift_id=shift.id,
                doctor_id=doc.id,
                status=AssignmentStatus.CONFIRMED,
                pay_amount=shift.base_pay,
                source="coordinator",
            ))
            assigned += 1

        if assigned > 0:
            shift.status = "filled" if assigned >= needed else "partially_filled"
            assigned_count += 1

    await session.flush()
    return assigned_count


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    await seed()

    async with async_session_factory() as session:
        # Guard: skip if already populated
        doc_count = await session.scalar(select(func.count()).select_from(Doctor))
        if doc_count and doc_count > 10:
            print(f"Test data already exists ({doc_count} doctors). Skipping.")
            return

        print("Loading reference data...")
        cert_res = await session.execute(select(CertificationType))
        cert_map = {c.name: c for c in cert_res.scalars().all()}

        lang_res = await session.execute(select(Language))
        lang_map = {l.code: l for l in lang_res.scalars().all()}

        cl_res = await session.execute(select(CodeLevel))
        cl_map = {c.code: c.id for c in cl_res.scalars().all()}

        print("Creating institutions...")
        sites_with_type = await create_institutions(session, cl_map, cert_map, lang_map)

        print("Creating 50 doctors...")
        doctors = await create_doctors(session, cert_map, lang_map, cl_map)
        print(f"  → {len(doctors)} doctors created")

        months = [date(2026, 4, 1), date(2026, 5, 1)]
        print(f"Creating shifts for April + May 2026 ({len(sites_with_type)} sites)...")
        shifts = await create_shifts(session, sites_with_type, months, cl_map)
        print(f"  → {len(shifts)} shifts created")

        print("Creating doctor availability...")
        await create_availability(session, doctors, months)

        print("Creating coordinator assignments (~30% of April shifts)...")
        n_assigned = await create_assignments(session, shifts, doctors)
        print(f"  → {n_assigned} shifts assigned by coordinator")

        await session.commit()
        print("\n✓ Test data generation complete.")
        print(f"  Doctors:      {len(doctors)}")
        print(f"  Sites:        {len(sites_with_type)}")
        print(f"  Shifts:       {len(shifts)}")
        print(f"  Assigned:     {n_assigned}")

        # Doctors eligible for Auronzo 118 (need ACLS + BLSD + vehicle)
        eligible_auronzo = [
            d for d in doctors
            if d.can_emergency_vehicle and d.can_work_alone
        ]
        print(f"\nEligible for PPI Auronzo 118: {len(eligible_auronzo)} doctors")
        for d in eligible_auronzo[:5]:
            print(f"  • {d.first_name} {d.last_name} – {d.years_experience}y exp")

        print(f"\nDoctor login: [email] / Medico2026!")
        print(f"Sample: {doctors[0].email}")


if __name__ == "__main__":
    asyncio.run(main())
