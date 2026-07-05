"""Async database access via SQLAlchemy ORM (Neon PostgreSQL + asyncpg driver)."""
from __future__ import annotations

import secrets
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from clinic.orm.engine import create_session_factory, get_async_engine, sanitize_dsn
from clinic.orm.tables import (
    Appointment as AppointmentRow,
)
from clinic.orm.tables import (
    AppointmentStatus,
    BlockedPeriod,
    Clinic as ClinicRow,
    Doctor as DoctorRow,
    DoctorSchedule,
    Patient as PatientRow,
    Specialty as SpecialtyRow,
)

from .availability import compute_available_slots
from .models import (
    Appointment,
    BookingError,
    Clinic,
    Doctor,
    Slot,
    SlotTakenError,
    Specialty,
)

_REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _make_reference() -> str:
    return "AAR-" + "".join(secrets.choice(_REFERENCE_ALPHABET) for _ in range(6))


def _clinic(row: ClinicRow) -> Clinic:
    return Clinic(
        id=str(row.id),
        name=row.name,
        timezone=row.timezone,
        phone=row.phone,
        address=row.address,
        opening_time=row.opening_time,
        closing_time=row.closing_time,
        slot_minutes=row.slot_minutes,
    )


def _doctor(row: DoctorRow, specialty_name: str) -> Doctor:
    return Doctor(
        id=str(row.id),
        name=row.name,
        specialty=specialty_name,
        qualifications=row.qualifications,
        languages=tuple(row.languages or ()),
    )


class Database:
    def __init__(self, dsn: str) -> None:
        self._dsn = sanitize_dsn(dsn)
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def connect(self) -> None:
        self._engine = get_async_engine(self._dsn)
        self._session_factory = create_session_factory(self._engine)

    async def close(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    def _session(self) -> AsyncSession:
        if self._session_factory is None:
            raise RuntimeError("Database.connect() was not called")
        return self._session_factory()

    # ---- reads -------------------------------------------------------------

    async def get_clinic(self) -> Clinic | None:
        async with self._session() as session:
            row = await session.scalar(select(ClinicRow).order_by(ClinicRow.created_at).limit(1))
            return _clinic(row) if row else None

    async def list_specialties(self) -> list[Specialty]:
        async with self._session() as session:
            rows = (await session.scalars(select(SpecialtyRow).order_by(SpecialtyRow.name))).all()
            return [Specialty(name=r.name, description=r.description) for r in rows]

    async def find_doctors(
        self, *, specialty: str | None = None, name: str | None = None
    ) -> list[Doctor]:
        stmt = (
            select(DoctorRow, SpecialtyRow.name.label("specialty_name"))
            .join(SpecialtyRow, DoctorRow.specialty_id == SpecialtyRow.id)
            .where(DoctorRow.active.is_(True))
            .order_by(DoctorRow.name)
        )
        if specialty:
            stmt = stmt.where(SpecialtyRow.name.ilike(f"%{specialty.strip()}%"))
        if name:
            stmt = stmt.where(DoctorRow.name.ilike(f"%{name.strip()}%"))

        async with self._session() as session:
            rows = (await session.execute(stmt)).all()
            return [_doctor(doc, spec) for doc, spec in rows]

    async def available_slots(
        self, *, doctor: Doctor, on_date: date, tz: ZoneInfo, slot_minutes: int, now: datetime
    ) -> list[Slot]:
        doctor_uuid = uuid.UUID(doctor.id)
        dow = int(on_date.strftime("%w"))
        day_start = datetime.combine(on_date, datetime.min.time(), tzinfo=tz)
        day_end = day_start + timedelta(days=1)

        async with self._session() as session:
            sched_rows = (
                await session.scalars(
                    select(DoctorSchedule).where(
                        DoctorSchedule.doctor_id == doctor_uuid,
                        DoctorSchedule.weekday == dow,
                    )
                )
            ).all()
            schedules = [(r.start_time, r.end_time) for r in sched_rows]
            if not schedules:
                return []

            blocked_rows = (
                await session.scalars(
                    select(BlockedPeriod).where(
                        BlockedPeriod.doctor_id == doctor_uuid,
                        BlockedPeriod.ends_at > day_start,
                        BlockedPeriod.starts_at < day_end,
                    )
                )
            ).all()
            blocked = [(r.starts_at, r.ends_at) for r in blocked_rows]

            booked_rows = (
                await session.scalars(
                    select(AppointmentRow.starts_at).where(
                        AppointmentRow.doctor_id == doctor_uuid,
                        AppointmentRow.status == AppointmentStatus.scheduled,
                        AppointmentRow.starts_at >= day_start,
                        AppointmentRow.starts_at < day_end,
                    )
                )
            ).all()
            booked = set(booked_rows)

        starts = compute_available_slots(
            on_date=on_date,
            now=now,
            tz=tz,
            schedules=schedules,
            slot_minutes=slot_minutes,
            blocked=blocked,
            booked_starts=booked,
        )
        return [
            Slot(
                doctor_id=doctor.id,
                doctor_name=doctor.name,
                specialty=doctor.specialty,
                starts_at=s,
                ends_at=s + timedelta(minutes=slot_minutes),
            )
            for s in starts
        ]

    async def find_appointment(self, *, reference: str, phone: str) -> Appointment | None:
        stmt = (
            select(AppointmentRow)
            .options(selectinload(AppointmentRow.doctor).selectinload(DoctorRow.specialty))
            .options(selectinload(AppointmentRow.patient))
            .join(PatientRow)
            .where(
                func.upper(AppointmentRow.booking_reference) == reference.strip().upper(),
                PatientRow.phone == phone.strip(),
            )
        )
        async with self._session() as session:
            row = await session.scalar(stmt)
            if row is None:
                return None
            return Appointment(
                booking_reference=row.booking_reference,
                doctor_name=row.doctor.name,
                specialty=row.doctor.specialty.name,
                patient_name=row.patient.name,
                phone=row.patient.phone,
                starts_at=row.starts_at,
                ends_at=row.ends_at,
                status=row.status.value,
            )

    # ---- writes -------------------------------------------------------------

    async def book(
        self,
        *,
        clinic: Clinic,
        doctor: Doctor,
        starts_at: datetime,
        ends_at: datetime,
        patient_name: str,
        phone: str,
        language: str,
    ) -> Appointment:
        async with self._session() as session:
            async with session.begin():
                patient_id = await session.scalar(
                    pg_insert(PatientRow)
                    .values(name=patient_name.strip(), phone=phone.strip())
                    .on_conflict_do_update(
                        index_elements=[PatientRow.phone],
                        set_={"name": patient_name.strip()},
                    )
                    .returning(PatientRow.id)
                )
                reference: str | None = None
                for _ in range(5):
                    ref = _make_reference()
                    try:
                        async with session.begin_nested():
                            row = AppointmentRow(
                                booking_reference=ref,
                                clinic_id=uuid.UUID(clinic.id),
                                doctor_id=uuid.UUID(doctor.id),
                                patient_id=patient_id,
                                starts_at=starts_at,
                                ends_at=ends_at,
                                language=language,
                                status=AppointmentStatus.scheduled,
                            )
                            session.add(row)
                            await session.flush()
                        reference = ref
                        break
                    except IntegrityError as exc:
                        if _is_reference_collision(exc):
                            continue
                        if _is_slot_taken(exc):
                            raise SlotTakenError("That time was just taken.") from exc
                        raise
                if reference is None:
                    raise BookingError("Could not generate a booking reference. Please try again.")

        return Appointment(
            booking_reference=reference,
            doctor_name=doctor.name,
            specialty=doctor.specialty,
            patient_name=patient_name.strip(),
            phone=phone.strip(),
            starts_at=starts_at,
            ends_at=ends_at,
            status="scheduled",
        )

    async def cancel(self, *, reference: str, phone: str) -> Appointment | None:
        appt = await self.find_appointment(reference=reference, phone=phone)
        if appt is None or appt.status != "scheduled":
            return appt
        async with self._session() as session:
            async with session.begin():
                await session.execute(
                    update(AppointmentRow)
                    .where(func.upper(AppointmentRow.booking_reference) == reference.strip().upper())
                    .values(status=AppointmentStatus.cancelled, updated_at=func.now())
                )
        return Appointment(**{**appt.__dict__, "status": "cancelled"})

    async def reschedule(
        self, *, reference: str, phone: str, starts_at: datetime, ends_at: datetime
    ) -> Appointment:
        appt = await self.find_appointment(reference=reference, phone=phone)
        if appt is None:
            raise BookingError("No matching appointment was found.")
        if appt.status != "scheduled":
            raise BookingError("That appointment is not active and cannot be rescheduled.")
        try:
            async with self._session() as session:
                async with session.begin():
                    await session.execute(
                        update(AppointmentRow)
                        .where(func.upper(AppointmentRow.booking_reference) == reference.strip().upper())
                        .values(starts_at=starts_at, ends_at=ends_at, updated_at=func.now())
                    )
        except IntegrityError as exc:
            if _is_slot_taken(exc):
                raise SlotTakenError("That time was just taken.") from exc
            raise
        return Appointment(**{**appt.__dict__, "starts_at": starts_at, "ends_at": ends_at})


def _is_reference_collision(exc: IntegrityError) -> bool:
    msg = str(exc.orig).lower()
    return "booking_reference" in msg or "appointments_booking_reference_key" in msg


def _is_slot_taken(exc: IntegrityError) -> bool:
    msg = str(exc.orig).lower()
    return "one_active_appointment_per_doctor_slot" in msg or (
        "unique" in msg and "doctor_id" in msg
    )
