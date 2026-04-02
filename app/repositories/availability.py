import uuid
from datetime import date, time
from typing import Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.availability import DoctorAvailability, DoctorUnavailability
from app.repositories.base import BaseRepository
from app.utils.enums import AvailabilityType


class AvailabilityRepository(BaseRepository[DoctorAvailability]):
    def __init__(self, session: AsyncSession):
        super().__init__(DoctorAvailability, session)

    async def is_available(self, doctor_id: uuid.UUID, target_date: date, start: time, end: time) -> bool:
        # Check no unavailability covering this date
        unav = await self.session.execute(
            select(DoctorUnavailability).where(
                DoctorUnavailability.doctor_id == doctor_id,
                DoctorUnavailability.start_date <= target_date,
                DoctorUnavailability.end_date >= target_date,
                DoctorUnavailability.is_approved == True,
            )
        )
        if unav.scalars().first():
            return False

        # Check positive availability exists covering the time
        avail = await self.session.execute(
            select(DoctorAvailability).where(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.date == target_date,
                DoctorAvailability.start_time <= start,
                DoctorAvailability.end_time >= end,
            )
        )
        return avail.scalars().first() is not None

    async def bulk_availability_for_shift(
        self,
        doctor_ids: list[uuid.UUID],
        target_date: date,
        start: time,
        end: time,
    ) -> dict[uuid.UUID, tuple[bool, bool, AvailabilityType | None]]:
        """Return dict[doctor_id -> (is_available, blocked_by_unavailability, availability_type)].

        blocked_by_unavailability=True means an approved unavailability period covers target_date.
        availability_type is set only when is_available=True.
        """
        if not doctor_ids:
            return {}

        # Step 1: doctors blocked by approved unavailability
        unav_result = await self.session.execute(
            select(DoctorUnavailability.doctor_id).where(
                DoctorUnavailability.doctor_id.in_(doctor_ids),
                DoctorUnavailability.start_date <= target_date,
                DoctorUnavailability.end_date >= target_date,
                DoctorUnavailability.is_approved == True,  # noqa: E712
            )
        )
        blocked: set[uuid.UUID] = set(unav_result.scalars().all())

        # Step 2: availability slots covering the full time window
        avail_result = await self.session.execute(
            select(DoctorAvailability.doctor_id, DoctorAvailability.availability_type).where(
                DoctorAvailability.doctor_id.in_(doctor_ids),
                DoctorAvailability.date == target_date,
                DoctorAvailability.start_time <= start,
                DoctorAvailability.end_time >= end,
            )
        )
        avail_map: dict[uuid.UUID, AvailabilityType] = {
            row.doctor_id: row.availability_type for row in avail_result.all()
        }

        out: dict[uuid.UUID, tuple[bool, bool, AvailabilityType | None]] = {}
        for did in doctor_ids:
            if did in blocked:
                out[did] = (False, True, None)
            elif did in avail_map:
                out[did] = (True, False, avail_map[did])
            else:
                out[did] = (False, False, None)
        return out

    async def bulk_availability_for_doctor_and_shifts(
        self,
        doctor_id: uuid.UUID,
        shifts: list,  # list[Shift] — avoids circular import
    ) -> dict[uuid.UUID, "AvailabilitySnapshot"]:
        """Return AvailabilitySnapshot keyed by shift_id for one doctor across many shifts.

        Fires 2 queries regardless of shift count.
        """
        from app.rules.eligibility import AvailabilitySnapshot  # local to avoid circular

        if not shifts:
            return {}

        shift_dates = list({s.date for s in shifts})
        min_date = min(shift_dates)
        max_date = max(shift_dates)

        # Q1: approved unavailability periods overlapping any shift date
        unav_result = await self.session.execute(
            select(DoctorUnavailability.start_date, DoctorUnavailability.end_date).where(
                DoctorUnavailability.doctor_id == doctor_id,
                DoctorUnavailability.start_date <= max_date,
                DoctorUnavailability.end_date >= min_date,
                DoctorUnavailability.is_approved == True,  # noqa: E712
            )
        )
        unavail_periods = [(row.start_date, row.end_date) for row in unav_result.all()]

        # Q2: availability slots on any shift date
        avail_result = await self.session.execute(
            select(
                DoctorAvailability.date,
                DoctorAvailability.start_time,
                DoctorAvailability.end_time,
                DoctorAvailability.availability_type,
            ).where(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.date.in_(shift_dates),
            )
        )
        slots_by_date: dict = {}
        for row in avail_result.all():
            slots_by_date.setdefault(row.date, []).append(
                (row.start_time, row.end_time, row.availability_type)
            )

        out: dict[uuid.UUID, AvailabilitySnapshot] = {}
        for shift in shifts:
            blocked = any(s_date <= shift.date <= e_date for s_date, e_date in unavail_periods)
            if blocked:
                out[shift.id] = AvailabilitySnapshot(
                    available=False, blocked_by_unavailability=True, availability_type=None
                )
                continue

            shift_start = shift.start_datetime.time()
            shift_end = shift.end_datetime.time()
            matched_type: AvailabilityType | None = None
            for slot_start, slot_end, slot_type in slots_by_date.get(shift.date, []):
                if slot_start <= shift_start and slot_end >= shift_end:
                    matched_type = slot_type
                    break

            out[shift.id] = AvailabilitySnapshot(
                available=matched_type is not None,
                blocked_by_unavailability=False,
                availability_type=matched_type,
            )

        return out

    async def bulk_availability_type_for_doctor_and_shifts(
        self,
        doctor_id: uuid.UUID,
        shifts: list,  # list[Shift]
    ) -> dict[uuid.UUID, AvailabilityType | None]:
        """Raw availability type per shift_id for scoring. 1 query.

        Does NOT check unavailability — preserves exact parity with
        get_availability_with_type() used by the original _score_availability().
        """
        if not shifts:
            return {}

        shift_dates = list({s.date for s in shifts})
        avail_result = await self.session.execute(
            select(
                DoctorAvailability.date,
                DoctorAvailability.start_time,
                DoctorAvailability.end_time,
                DoctorAvailability.availability_type,
            ).where(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.date.in_(shift_dates),
            )
        )
        slots_by_date: dict = {}
        for row in avail_result.all():
            slots_by_date.setdefault(row.date, []).append(
                (row.start_time, row.end_time, row.availability_type)
            )

        out: dict[uuid.UUID, AvailabilityType | None] = {}
        for shift in shifts:
            shift_start = shift.start_datetime.time()
            shift_end = shift.end_datetime.time()
            matched_type: AvailabilityType | None = None
            for slot_start, slot_end, slot_type in slots_by_date.get(shift.date, []):
                if slot_start <= shift_start and slot_end >= shift_end:
                    matched_type = slot_type
                    break
            out[shift.id] = matched_type
        return out

    async def get_availability_with_type(
        self, doctor_id: uuid.UUID, target_date: date, start: time, end: time
    ) -> DoctorAvailability | None:
        result = await self.session.execute(
            select(DoctorAvailability).where(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.date == target_date,
                DoctorAvailability.start_time <= start,
                DoctorAvailability.end_time >= end,
            )
        )
        return result.scalars().first()

    async def get_by_doctor_and_date_range(
        self, doctor_id: uuid.UUID, start: date, end: date
    ) -> Sequence[DoctorAvailability]:
        result = await self.session.execute(
            select(DoctorAvailability).where(
                DoctorAvailability.doctor_id == doctor_id,
                DoctorAvailability.date >= start,
                DoctorAvailability.date <= end,
            )
        )
        return result.scalars().all()

    async def bulk_create(self, doctor_id: uuid.UUID, entries: list[dict]) -> list[DoctorAvailability]:
        created = []
        for entry in entries:
            avail = DoctorAvailability(doctor_id=doctor_id, **entry)
            self.session.add(avail)
            created.append(avail)
        await self.session.flush()
        return created

    # Unavailability
    async def get_unavailability_by_id(self, id: int) -> DoctorUnavailability | None:
        return await self.session.get(DoctorUnavailability, id)

    async def create_unavailability(self, doctor_id: uuid.UUID, **kwargs) -> DoctorUnavailability:
        unav = DoctorUnavailability(doctor_id=doctor_id, **kwargs)
        self.session.add(unav)
        await self.session.flush()
        await self.session.refresh(unav)
        return unav

    async def get_unavailabilities(
        self, doctor_id: uuid.UUID, start: date | None = None, end: date | None = None
    ) -> Sequence[DoctorUnavailability]:
        stmt = select(DoctorUnavailability).where(DoctorUnavailability.doctor_id == doctor_id)
        if start:
            stmt = stmt.where(DoctorUnavailability.end_date >= start)
        if end:
            stmt = stmt.where(DoctorUnavailability.start_date <= end)
        result = await self.session.execute(stmt)
        return result.scalars().all()
