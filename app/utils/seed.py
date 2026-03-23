"""Seed reference data: certification types, languages, code levels, admin user, demo medico."""
import asyncio
from datetime import date, timedelta

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.doctor import (
    CertificationType,
    Doctor,
    DoctorCertification,
    DoctorLanguage,
    DoctorPreference,
    Language,
)
from app.models.requirement import CodeLevel
from app.models.user import User
from app.utils.enums import HomologationStatus, UserRole

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
    {"code": "RED", "description": "Codice Rosso - Emergency", "severity_order": 4},
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

        # Default admin users
        for admin_email, admin_pass in [
            ("datoffaletti@gmail.com", "Toffaletti26"),
            ("admin", "admin"),
        ]:
            existing_admin = await session.execute(
                select(User).where(User.email == admin_email)
            )
            if not existing_admin.scalar_one_or_none():
                session.add(User(
                    email=admin_email,
                    password_hash=hash_password(admin_pass),
                    role=UserRole.ADMIN,
                ))

        # Demo medico account
        demo_email = "medico@demo.com"
        existing_demo = await session.execute(
            select(User).where(User.email == demo_email)
        )
        if not existing_demo.scalar_one_or_none():
            demo_user = User(
                email=demo_email,
                password_hash=hash_password("medico123"),
                role=UserRole.MEDICO,
            )
            session.add(demo_user)
            await session.flush()

            # Query reference data
            cl_result = await session.execute(
                select(CodeLevel).where(CodeLevel.code == "YELLOW")
            )
            yellow_cl = cl_result.scalar_one_or_none()

            demo_doctor = Doctor(
                user_id=demo_user.id,
                fiscal_code="BNCLRA85M45H501Z",
                first_name="Laura",
                last_name="Bianchi",
                email=demo_email,
                phone="+39 345 1234567",
                password_hash=demo_user.password_hash,
                lat=41.9028,
                lon=12.4964,
                max_distance_km=50.0,
                willing_to_relocate=False,
                willing_overnight_stay=True,
                max_shifts_per_month=15,
                max_night_shifts_per_month=6,
                max_code_level_id=yellow_cl.id if yellow_cl else None,
                can_work_alone=True,
                can_emergency_vehicle=False,
                years_experience=5,
                birth_date=date(1985, 8, 5),
                residence_address="Via dei Condotti 42, 00187 Roma RM",
                domicile_city="Roma",
                homologation_status=HomologationStatus.APPROVED,
                ordine_province="RM",
                ordine_number="12345",
                has_own_vehicle=True,
                profile_completion_percent=85,
            )
            session.add(demo_doctor)
            await session.flush()

            # Certifications: BLSD, ACLS, PALS
            for cert_name, days_ago in [("BLSD", 400), ("ACLS", 300), ("PALS", 200)]:
                ct_result = await session.execute(
                    select(CertificationType).where(CertificationType.name == cert_name)
                )
                ct = ct_result.scalar_one_or_none()
                if ct:
                    obtained = date.today() - timedelta(days=days_ago)
                    expiry = obtained + timedelta(days=(ct.validity_months or 24) * 30)
                    session.add(DoctorCertification(
                        doctor_id=demo_doctor.id,
                        certification_type_id=ct.id,
                        obtained_date=obtained,
                        expiry_date=expiry,
                        is_active=True,
                    ))

            # Languages: Italian (native), English (intermediate)
            for lang_code, level in [("it", 5), ("en", 3)]:
                lang_result = await session.execute(
                    select(Language).where(Language.code == lang_code)
                )
                lang = lang_result.scalar_one_or_none()
                if lang:
                    session.add(DoctorLanguage(
                        doctor_id=demo_doctor.id,
                        language_id=lang.id,
                        proficiency_level=level,
                    ))

            # Preferences
            session.add(DoctorPreference(
                doctor_id=demo_doctor.id,
                prefers_day=True,
                prefers_night=False,
                prefers_weekends=False,
                avoids_weekends=True,
                min_pay_per_shift=400.0,
                max_preferred_distance_km=40.0,
            ))

            print("Demo medico account created: medico@demo.com / medico123")

        await session.commit()
        print("Seed data loaded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
