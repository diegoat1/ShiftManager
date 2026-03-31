"""Seed reference data: certification types, languages, code levels, admin user, institutions."""
import asyncio

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.doctor import (
    CertificationType,
    Language,
)
from app.models.institution import Institution, InstitutionSite
from app.models.requirement import CodeLevel, InstitutionLanguageRequirement
from app.models.user import User
from app.utils.enums import UserRole

CERTIFICATION_TYPES = [
    {"name": "BLSD", "description": "Basic Life Support Defibrillation", "validity_months": 24},
    {"name": "ACLS", "description": "Advanced Cardiovascular Life Support", "validity_months": 24},
    {"name": "PALS", "description": "Pediatric Advanced Life Support", "validity_months": 24},
    {"name": "PTC", "description": "Pre-Hospital Trauma Care", "validity_months": 36},
    {"name": "ATLS", "description": "Advanced Trauma Life Support", "validity_months": 48},
    {"name": "ECG_ADVANCED", "description": "Advanced ECG interpretation", "validity_months": None},
    {"name": "EMERGENCY_MEDICINE_EXPERIENCE", "description": "Pronto Soccorso experience", "validity_months": None},
    {"name": "GUARDIA_MEDICA_EXPERIENCE", "description": "Guardia Medica experience", "validity_months": None},
    {"name": "118_EXPERIENCE", "description": "Servizio 118 emergency experience", "validity_months": None},
    {"name": "PEDIATRIC_EMERGENCY_EXPERIENCE", "description": "Pediatric emergency experience", "validity_months": None},
]

LANGUAGES = [
    {"code": "it", "name": "Italiano"},
    {"code": "en", "name": "English"},
    {"code": "fr", "name": "Français"},
    {"code": "de", "name": "Deutsch"},
    {"code": "es", "name": "Español"},
    {"code": "ro", "name": "Română"},
    {"code": "ar", "name": "العربية"},
    {"code": "zh", "name": "中文"},
]

CODE_LEVELS = [
    {"code": "WHITE", "description": "1 - Bianco (Non urgente)", "severity_order": 1},
    {"code": "GREEN", "description": "2 - Verde (Urgenza minore)", "severity_order": 2},
    {"code": "BLUE", "description": "3 - Giallo/Azzurro (Urgente)", "severity_order": 3},
    {"code": "ORANGE", "description": "4 - Arancione (Alta urgenza)", "severity_order": 4},
    {"code": "RED", "description": "5 - Rosso (Emergenza)", "severity_order": 5},
]


async def seed():
    async with async_session_factory() as session:
        # Certification types
        for ct_data in CERTIFICATION_TYPES:
            existing = await session.execute(
                select(CertificationType).where(CertificationType.name == ct_data["name"])
            )
            if not existing.scalar_one_or_none():
                session.add(CertificationType(**ct_data))

        # Languages
        for lang_data in LANGUAGES:
            existing = await session.execute(
                select(Language).where(Language.code == lang_data["code"])
            )
            if not existing.scalar_one_or_none():
                session.add(Language(**lang_data))

        # Code levels
        for cl_data in CODE_LEVELS:
            existing = await session.execute(
                select(CodeLevel).where(CodeLevel.code == cl_data["code"])
            )
            if not existing.scalar_one_or_none():
                session.add(CodeLevel(**cl_data))

        # Main admin user
        existing_admin = await session.execute(
            select(User).where(User.email == "datoffaletti@gmail.com")
        )
        if not existing_admin.scalar_one_or_none():
            session.add(User(
                email="datoffaletti@gmail.com",
                password_hash=hash_password("Toffaletti26"),
                role=UserRole.ADMIN,
            ))

        # ASU FC – PS di Tolmezzo
        existing_inst = await session.execute(
            select(Institution).where(Institution.tax_code == "02985660303")
        )
        if not existing_inst.scalar_one_or_none():
            inst = Institution(
                name="Azienda Sanitaria Universitaria Friuli Centrale (ASU FC)",
                tax_code="02985660303",
                address="Via Pozzuolo, 330",
                city="Udine",
                province="UD",
                institution_type="pronto_soccorso",
            )
            session.add(inst)
            await session.flush()

            # min_code_level: GREEN (codici bianchi e verdi)
            cl_res = await session.execute(
                select(CodeLevel).where(CodeLevel.code == "GREEN")
            )
            green_cl = cl_res.scalar_one_or_none()

            site = InstitutionSite(
                institution_id=inst.id,
                name="Presidio Ospedaliero di Tolmezzo - S. Antonio Abate",
                address="Via Morgagni, 18",
                city="Tolmezzo",
                province="UD",
                lat=46.4022,
                lon=13.0139,
                min_code_level_id=green_cl.id if green_cl else None,
                requires_independent_work=True,
                min_years_experience=0,
            )
            session.add(site)
            await session.flush()

            # Italian B1 language requirement
            lang_res = await session.execute(
                select(Language).where(Language.code == "it")
            )
            italian = lang_res.scalar_one_or_none()
            if italian:
                session.add(InstitutionLanguageRequirement(
                    institution_id=inst.id,
                    language_id=italian.id,
                    min_proficiency=2,  # B1
                ))

            print("ASU FC / PS di Tolmezzo created.")

        await session.commit()
        print("Seed data loaded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
