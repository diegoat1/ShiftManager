"""Delete all test doctors (email ending in @medici.test).

Usage: python -m app.utils.cleanup_test_doctors
"""
import asyncio

from sqlalchemy import delete, select

from app.core.database import async_session_factory
from app.models.cooperative import Cooperative  # noqa: F401 — needed for relationship resolution
from app.models.doctor import Doctor
from app.models.user import User


async def cleanup() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(User).where(User.email.like("%@medici.test"))
        )
        users = result.scalars().all()
        print(f"Found {len(users)} test users to delete:")
        for u in users:
            print(f"  - {u.email}")

        if not users:
            print("Nothing to delete.")
            return

        user_ids = [u.id for u in users]

        # Delete doctors first (FK doctors.user_id → users.id, no cascade)
        await session.execute(
            delete(Doctor).where(Doctor.user_id.in_(user_ids))
        )

        await session.execute(
            delete(User).where(User.email.like("%@medici.test"))
        )
        await session.commit()
        print(f"Deleted {len(users)} test users and their doctor profiles.")


if __name__ == "__main__":
    asyncio.run(cleanup())
