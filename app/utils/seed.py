"""Seed reference data: certification types, languages, code levels, admin user."""
import asyncio

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.doctor import (
    CertificationType,
    Language,
)
from app.models.requirement import CodeLevel
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
    {"code": "WHITE", "description": "Codice Bianco - Non-urgent", "severity_order": 1},
    {"code": "GREEN", "description": "Codice Verde - Minor urgency", "severity_order": 2},
    {"code": "YELLOW", "description": "Codice Giallo - Urgent", "severity_order": 3},
    {"code": "BLUE", "description": "Codice Azzurro - High urgency", "severity_order": 4},
    {"code": "RED", "description": "Codice Rosso - Emergency", "severity_order": 5},
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

        await session.commit()
        print("Seed data loaded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
