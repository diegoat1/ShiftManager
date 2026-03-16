"""Generate realistic Italian medical scheduling data.

Usage: python -m app.utils.generate_data
"""
import asyncio
import json
import random
import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import select

from app.core.database import async_session_factory
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
from app.models.requirement import CodeLevel
from app.models.shift import Shift, ShiftRequirement
from app.utils.enums import AvailabilityType, InstitutionType, ShiftStatus, ShiftType
from app.utils.seed import seed

random.seed(42)

# --- Reference data ---

ITALIAN_FIRST_NAMES_M = [
    "Marco", "Luca", "Alessandro", "Giuseppe", "Andrea", "Francesco", "Matteo",
    "Lorenzo", "Davide", "Stefano", "Simone", "Fabio", "Antonio", "Giovanni",
    "Roberto", "Paolo", "Massimo", "Enrico", "Claudio", "Federico",
]
ITALIAN_FIRST_NAMES_F = [
    "Maria", "Giulia", "Francesca", "Sara", "Valentina", "Chiara", "Laura",
    "Elena", "Alessandra", "Silvia", "Federica", "Anna", "Martina", "Paola",
    "Roberta", "Monica", "Cristina", "Barbara", "Elisa", "Ilaria",
]
ITALIAN_LAST_NAMES = [
    "Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo",
    "Ricci", "Marino", "Greco", "Bruno", "Gallo", "Conti", "De Luca",
    "Mancini", "Costa", "Giordano", "Mazza", "Rizzo", "Lombardi",
    "Moretti", "Barbieri", "Fontana", "Santoro", "Mariani",
]

ITALIAN_CITIES = [
    {"name": "Roma", "province": "RM", "lat": 41.9028, "lon": 12.4964},
    {"name": "Milano", "province": "MI", "lat": 45.4642, "lon": 9.1900},
    {"name": "Napoli", "province": "NA", "lat": 40.8518, "lon": 14.2681},
    {"name": "Torino", "province": "TO", "lat": 45.0703, "lon": 7.6869},
    {"name": "Firenze", "province": "FI", "lat": 43.7696, "lon": 11.2558},
    {"name": "Bologna", "province": "BO", "lat": 44.4949, "lon": 11.3426},
    {"name": "Palermo", "province": "PA", "lat": 38.1157, "lon": 13.3615},
    {"name": "Genova", "province": "GE", "lat": 44.4056, "lon": 8.9463},
    {"name": "Bari", "province": "BA", "lat": 41.1171, "lon": 16.8719},
    {"name": "Verona", "province": "VR", "lat": 45.4384, "lon": 10.9916},
]

INSTITUTION_CONFIGS = [
    {
        "type": InstitutionType.PRONTO_SOCCORSO,
        "name_tpl": "Ospedale {city} - Pronto Soccorso",
        "sites": [
            {"name_tpl": "PS Centrale", "requires_independent_work": False, "requires_emergency_vehicle": False, "min_exp": 2},
            {"name_tpl": "PS Pediatrico", "requires_independent_work": False, "requires_emergency_vehicle": False, "min_exp": 3},
        ],
    },
    {
        "type": InstitutionType.PUNTO_PRIMO_INTERVENTO,
        "name_tpl": "PPI {city}",
        "sites": [
            {"name_tpl": "PPI Centro", "requires_independent_work": True, "requires_emergency_vehicle": False, "min_exp": 1},
            {"name_tpl": "PPI Periferia", "requires_independent_work": True, "requires_emergency_vehicle": False, "min_exp": 1},
        ],
    },
    {
        "type": InstitutionType.GUARDIA_MEDICA,
        "name_tpl": "Guardia Medica {city}",
        "sites": [
            {"name_tpl": "GM Distretto Nord", "requires_independent_work": True, "requires_emergency_vehicle": False, "min_exp": 0},
            {"name_tpl": "GM Distretto Sud", "requires_independent_work": True, "requires_emergency_vehicle": False, "min_exp": 0},
        ],
    },
    {
        "type": InstitutionType.EMERGENZA_118,
        "name_tpl": "Centrale 118 {city}",
        "sites": [
            {"name_tpl": "Postazione Alpha", "requires_independent_work": True, "requires_emergency_vehicle": True, "min_exp": 3},
            {"name_tpl": "Postazione Bravo", "requires_independent_work": True, "requires_emergency_vehicle": True, "min_exp": 2},
        ],
    },
    {
        "type": InstitutionType.CASA_DI_COMUNITA,
        "name_tpl": "Casa della Comunità {city}",
        "sites": [
            {"name_tpl": "CdC Ambulatorio", "requires_independent_work": True, "requires_emergency_vehicle": False, "min_exp": 0},
        ],
    },
    {
        "type": InstitutionType.RSA,
        "name_tpl": "RSA Villa Serena {city}",
        "sites": [
            {"name_tpl": "RSA Reparto A", "requires_independent_work": True, "requires_emergency_vehicle": False, "min_exp": 0},
            {"name_tpl": "RSA Reparto B", "requires_independent_work": True, "requires_emergency_vehicle": False, "min_exp": 0},
        ],
    },
]

# Shift templates per institution type
SHIFT_TEMPLATES = {
    InstitutionType.PRONTO_SOCCORSO: [
        {"start": time(7, 0), "end": time(19, 0), "type": ShiftType.DAY, "is_night": False, "pay": 600, "docs": 2, "priority": 2},
        {"start": time(19, 0), "end": time(7, 0), "type": ShiftType.NIGHT, "is_night": True, "pay": 800, "docs": 2, "priority": 1},
    ],
    InstitutionType.PUNTO_PRIMO_INTERVENTO: [
        {"start": time(8, 0), "end": time(20, 0), "type": ShiftType.DAY, "is_night": False, "pay": 450, "docs": 1, "priority": 3},
        {"start": time(20, 0), "end": time(8, 0), "type": ShiftType.NIGHT, "is_night": True, "pay": 600, "docs": 1, "priority": 2},
    ],
    InstitutionType.GUARDIA_MEDICA: [
        {"start": time(20, 0), "end": time(8, 0), "type": ShiftType.NIGHT, "is_night": True, "pay": 400, "docs": 1, "priority": 4},
        {"start": time(8, 0), "end": time(20, 0), "type": ShiftType.WEEKEND_DAY, "is_night": False, "pay": 350, "docs": 1, "priority": 4},
    ],
    InstitutionType.EMERGENZA_118: [
        {"start": time(7, 0), "end": time(19, 0), "type": ShiftType.DAY, "is_night": False, "pay": 700, "docs": 1, "priority": 1},
        {"start": time(19, 0), "end": time(7, 0), "type": ShiftType.NIGHT, "is_night": True, "pay": 900, "docs": 1, "priority": 1},
    ],
    InstitutionType.CASA_DI_COMUNITA: [
        {"start": time(8, 0), "end": time(14, 0), "type": ShiftType.DAY, "is_night": False, "pay": 250, "docs": 1, "priority": 5},
        {"start": time(14, 0), "end": time(20, 0), "type": ShiftType.EVENING, "is_night": False, "pay": 280, "docs": 1, "priority": 5},
    ],
    InstitutionType.RSA: [
        {"start": time(8, 0), "end": time(20, 0), "type": ShiftType.DAY, "is_night": False, "pay": 350, "docs": 1, "priority": 4},
        {"start": time(20, 0), "end": time(8, 0), "type": ShiftType.NIGHT, "is_night": True, "pay": 450, "docs": 1, "priority": 3},
    ],
}


def _generate_fiscal_code(i: int) -> str:
    """Generate a fake but format-valid Italian fiscal code."""
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    base = f"{''.join(random.choices(letters, k=6))}{random.randint(60, 99)}{'ABCDEHLMPRST'[i % 12]}{random.randint(1, 28):02d}"
    base += f"H{random.randint(100, 999)}{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[i % 26]}"
    return base[:16]


async def generate_doctors(session, cert_map: dict, lang_map: dict, code_level_map: dict, n: int = 50):
    """Generate n doctors with realistic Italian profiles."""
    doctors = []
    all_names = ITALIAN_FIRST_NAMES_M + ITALIAN_FIRST_NAMES_F

    for i in range(n):
        first_name = all_names[i % len(all_names)]
        last_name = ITALIAN_LAST_NAMES[i % len(ITALIAN_LAST_NAMES)]
        city = ITALIAN_CITIES[i % len(ITALIAN_CITIES)]
        years_exp = random.choices([0, 1, 2, 3, 5, 8, 10, 15, 20], weights=[5, 8, 10, 12, 15, 15, 12, 8, 5])[0]

        # Code level based on experience
        if years_exp >= 10:
            max_cl_code = "RED"
        elif years_exp >= 5:
            max_cl_code = "YELLOW"
        elif years_exp >= 2:
            max_cl_code = "GREEN"
        else:
            max_cl_code = "WHITE"

        max_cl = code_level_map.get(max_cl_code)

        doctor = Doctor(
            fiscal_code=_generate_fiscal_code(i),
            first_name=first_name,
            last_name=last_name,
            email=f"{first_name.lower()}.{last_name.lower()}.{i}@medici.it",
            password_hash="$2b$12$fakehashfakehashfakehashfakehashfakehashfakehashfa",
            phone=f"+39 {random.randint(300, 399)} {random.randint(1000000, 9999999)}",
            lat=city["lat"] + random.uniform(-0.15, 0.15),
            lon=city["lon"] + random.uniform(-0.15, 0.15),
            max_distance_km=random.choice([30, 50, 80, 100, 150]),
            willing_to_relocate=random.random() < 0.25,
            willing_overnight_stay=random.random() < 0.35,
            max_shifts_per_month=random.choice([8, 10, 12, 15, 20]),
            max_night_shifts_per_month=random.choice([None, None, 4, 6, 8]),
            max_code_level_id=max_cl.id if max_cl else None,
            can_work_alone=years_exp >= 2 or random.random() < 0.2,
            can_emergency_vehicle=years_exp >= 3 and random.random() < 0.5,
            years_experience=years_exp,
            is_active=True,
        )
        session.add(doctor)
        await session.flush()

        # Certifications based on experience
        cert_names_for_doctor = ["BLSD"]
        if years_exp >= 2:
            cert_names_for_doctor.append("ACLS")
        if years_exp >= 3:
            if random.random() < 0.5:
                cert_names_for_doctor.append("PALS")
            if random.random() < 0.4:
                cert_names_for_doctor.append("PTC")
        if years_exp >= 5:
            if random.random() < 0.3:
                cert_names_for_doctor.append("ATLS")
            if random.random() < 0.4:
                cert_names_for_doctor.append("ECG_ADVANCED")
        if years_exp >= 8:
            if random.random() < 0.5:
                cert_names_for_doctor.append("EMERGENCY_MEDICINE_EXPERIENCE")

        for cert_name in cert_names_for_doctor:
            ct = cert_map.get(cert_name)
            if not ct:
                continue
            obtained = date.today() - timedelta(days=random.randint(180, years_exp * 365 + 365))
            expiry = obtained + timedelta(days=ct.validity_months * 30) if ct.validity_months else None
            session.add(DoctorCertification(
                doctor_id=doctor.id,
                certification_type_id=ct.id,
                obtained_date=obtained,
                expiry_date=expiry,
                is_active=True if not expiry or expiry > date.today() else False,
            ))

        # Languages: everyone speaks Italian, some speak others
        it_lang = lang_map.get("it")
        if it_lang:
            session.add(DoctorLanguage(doctor_id=doctor.id, language_id=it_lang.id, proficiency_level=5))
        if random.random() < 0.6:
            en_lang = lang_map.get("en")
            if en_lang:
                session.add(DoctorLanguage(doctor_id=doctor.id, language_id=en_lang.id, proficiency_level=random.choice([2, 3, 4])))
        if random.random() < 0.15:
            extra_codes = [c for c in ["fr", "de", "es", "ro", "ar"] if c in lang_map]
            if extra_codes:
                code = random.choice(extra_codes)
                session.add(DoctorLanguage(doctor_id=doctor.id, language_id=lang_map[code].id, proficiency_level=random.choice([2, 3])))

        # Preferences
        pref = DoctorPreference(
            doctor_id=doctor.id,
            prefers_day=random.random() < 0.6,
            prefers_night=random.random() < 0.3,
            prefers_weekends=random.random() < 0.2,
            avoids_weekends=random.random() < 0.4,
            min_pay_per_shift=random.choice([None, 300, 400, 500]),
            max_preferred_distance_km=random.choice([None, 30, 50, 80]),
        )
        session.add(pref)

        doctors.append(doctor)

    await session.flush()
    return doctors


async def generate_institutions(session, code_level_map: dict, cities: list[dict] | None = None):
    """Generate 6 institutions (one per type) with sites."""
    if cities is None:
        cities = ITALIAN_CITIES[:6]

    institutions = []
    all_sites = []

    for idx, config in enumerate(INSTITUTION_CONFIGS):
        city = cities[idx % len(cities)]
        inst = Institution(
            name=config["name_tpl"].format(city=city["name"]),
            tax_code=f"{random.randint(10000000000, 99999999999):011d}{idx:05d}",
            address=f"Via {'Roma Firenze Milano Napoli Torino Bologna'.split()[idx % 6]} {random.randint(1, 200)}",
            city=city["name"],
            province=city["province"],
            institution_type=config["type"].value,
        )
        session.add(inst)
        await session.flush()

        # Determine min code level for this institution type
        type_to_code = {
            InstitutionType.PRONTO_SOCCORSO: "YELLOW",
            InstitutionType.PUNTO_PRIMO_INTERVENTO: "GREEN",
            InstitutionType.GUARDIA_MEDICA: "WHITE",
            InstitutionType.EMERGENZA_118: "RED",
            InstitutionType.CASA_DI_COMUNITA: "WHITE",
            InstitutionType.RSA: "WHITE",
        }
        min_cl = code_level_map.get(type_to_code.get(config["type"], "WHITE"))

        for site_cfg in config["sites"]:
            site = InstitutionSite(
                institution_id=inst.id,
                name=site_cfg["name_tpl"],
                address=inst.address,
                city=city["name"],
                province=city["province"],
                lat=city["lat"] + random.uniform(-0.05, 0.05),
                lon=city["lon"] + random.uniform(-0.05, 0.05),
                lodging_available=random.random() < 0.3,
                meal_support=random.random() < 0.5,
                parking_available=random.random() < 0.7,
                min_code_level_id=min_cl.id if min_cl else None,
                requires_independent_work=site_cfg["requires_independent_work"],
                requires_emergency_vehicle=site_cfg["requires_emergency_vehicle"],
                min_years_experience=site_cfg["min_exp"],
            )
            session.add(site)
            all_sites.append((site, config["type"]))

        institutions.append(inst)

    await session.flush()
    return institutions, all_sites


async def generate_shifts(session, sites_with_type: list, target_month: date, code_level_map: dict):
    """Generate shifts for all sites for the target month."""
    shifts = []
    first_day = target_month.replace(day=1)
    if first_day.month == 12:
        last_day = first_day.replace(year=first_day.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = first_day.replace(month=first_day.month + 1, day=1) - timedelta(days=1)

    for site, inst_type in sites_with_type:
        templates = SHIFT_TEMPLATES.get(inst_type, [])
        current = first_day
        while current <= last_day:
            for tmpl in templates:
                # Guardia Medica weekday nights only on weekdays, weekend shifts on weekends
                is_weekend = current.weekday() >= 5
                if inst_type == InstitutionType.GUARDIA_MEDICA:
                    if tmpl["type"] == ShiftType.WEEKEND_DAY and not is_weekend:
                        continue
                    if tmpl["type"] == ShiftType.NIGHT and is_weekend:
                        continue

                start_dt = datetime.combine(current, tmpl["start"])
                end_dt = datetime.combine(current, tmpl["end"])
                if tmpl["end"] <= tmpl["start"]:
                    end_dt += timedelta(days=1)

                # Inherit site fields
                min_cl_id = site.min_code_level_id
                type_to_code = {
                    InstitutionType.PRONTO_SOCCORSO: "YELLOW",
                    InstitutionType.EMERGENZA_118: "RED",
                }
                if inst_type in type_to_code and tmpl["is_night"]:
                    night_cl = code_level_map.get(type_to_code[inst_type])
                    if night_cl:
                        min_cl_id = night_cl.id

                shift = Shift(
                    site_id=site.id,
                    date=current,
                    start_datetime=start_dt,
                    end_datetime=end_dt,
                    required_doctors=tmpl["docs"],
                    status=ShiftStatus.OPEN,
                    base_pay=tmpl["pay"],
                    is_night=tmpl["is_night"],
                    shift_type=tmpl["type"].value,
                    priority=tmpl["priority"],
                    min_code_level_id=min_cl_id,
                    requires_independent_work=site.requires_independent_work,
                    requires_emergency_vehicle=site.requires_emergency_vehicle,
                    min_years_experience=site.min_years_experience,
                )
                session.add(shift)
                shifts.append(shift)

            current += timedelta(days=1)

    await session.flush()
    return shifts


async def generate_availability(session, doctors: list, target_month: date):
    """Generate availability for each doctor for the target month."""
    first_day = target_month.replace(day=1)
    if first_day.month == 12:
        last_day = first_day.replace(year=first_day.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = first_day.replace(month=first_day.month + 1, day=1) - timedelta(days=1)

    count = 0
    for doctor in doctors:
        current = first_day
        while current <= last_day:
            is_weekend = current.weekday() >= 5

            # 72% of days available
            if random.random() < 0.72:
                # Day slot
                if random.random() < 0.8:
                    session.add(DoctorAvailability(
                        doctor_id=doctor.id,
                        date=current,
                        start_time=time(7, 0),
                        end_time=time(20, 0),
                        availability_type=AvailabilityType.AVAILABLE,
                    ))
                    count += 1

                # Night slot
                if random.random() < 0.4:
                    session.add(DoctorAvailability(
                        doctor_id=doctor.id,
                        date=current,
                        start_time=time(19, 0),
                        end_time=time(23, 59),
                        availability_type=AvailabilityType.AVAILABLE,
                    ))
                    count += 1

                # Weekend reluctance
                if is_weekend and random.random() < 0.5:
                    session.add(DoctorAvailability(
                        doctor_id=doctor.id,
                        date=current,
                        start_time=time(0, 0),
                        end_time=time(23, 59),
                        availability_type=AvailabilityType.RELUCTANT,
                    ))
                    count += 1

            current += timedelta(days=1)

        # Flush every 10 doctors to avoid huge transaction
        if count > 500:
            await session.flush()
            count = 0

    await session.flush()


def _export_json(doctors, institutions, shifts, filepath: str = "italy_medical_scheduling_seed.json"):
    """Export generated data summary to JSON for inspection."""
    data = {
        "doctors": [
            {
                "name": f"{d.first_name} {d.last_name}",
                "fiscal_code": d.fiscal_code,
                "city_lat_lon": [d.lat, d.lon],
                "years_experience": d.years_experience,
                "can_work_alone": d.can_work_alone,
                "can_emergency_vehicle": d.can_emergency_vehicle,
                "max_shifts_per_month": d.max_shifts_per_month,
            }
            for d in doctors
        ],
        "institutions": [
            {
                "name": inst.name,
                "type": inst.institution_type,
                "city": inst.city,
            }
            for inst in institutions
        ],
        "shifts_count": len(shifts),
        "shifts_sample": [
            {
                "date": str(s.date),
                "shift_type": s.shift_type,
                "is_night": s.is_night,
                "priority": s.priority,
                "base_pay": s.base_pay,
            }
            for s in shifts[:20]
        ],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Exported summary to {filepath}")


async def main():
    # Ensure seed data exists
    await seed()

    async with async_session_factory() as session:
        # Load reference data
        cert_result = await session.execute(select(CertificationType))
        cert_map = {ct.name: ct for ct in cert_result.scalars().all()}

        lang_result = await session.execute(select(Language))
        lang_map = {l.code: l for l in lang_result.scalars().all()}

        cl_result = await session.execute(select(CodeLevel))
        code_level_map = {cl.code: cl for cl in cl_result.scalars().all()}

        print("Generating 50 doctors...")
        doctors = await generate_doctors(session, cert_map, lang_map, code_level_map, n=50)

        print("Generating 6 institutions with ~13 sites...")
        institutions, sites_with_type = await generate_institutions(session, code_level_map)

        target_month = date(2026, 4, 1)
        print(f"Generating shifts for {target_month.strftime('%B %Y')}...")
        shifts = await generate_shifts(session, sites_with_type, target_month, code_level_map)

        print(f"Generating availability for {len(doctors)} doctors...")
        await generate_availability(session, doctors, target_month)

        await session.commit()

        print(f"\nGenerated: {len(doctors)} doctors, {len(institutions)} institutions, "
              f"{len(sites_with_type)} sites, {len(shifts)} shifts")

        _export_json(doctors, institutions, shifts)
        print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
