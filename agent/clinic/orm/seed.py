"""Idempotent demo seed data (replaces 002_seed.sql)."""
from __future__ import annotations

from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .tables import Clinic, Doctor, DoctorSchedule, Specialty

CLINIC_NAME = "Aarogya Family Clinic"

SPECIALTIES: list[tuple[str, str]] = [
    ("General Medicine", "Primary care for adults and routine health concerns"),
    ("Pediatrics", "Medical care for infants, children and adolescents"),
    ("Dermatology", "Skin, hair and nail care"),
    ("Cardiology", "Heart and cardiovascular consultations"),
    ("Orthopedics", "Bones, joints and musculoskeletal care"),
]

DOCTORS: list[tuple[str, str, str, list[str]]] = [
    ("Dr. Ananya Rao", "General Medicine", "MBBS, MD", ["English", "Hindi", "Telugu"]),
    ("Dr. Vikram Singh", "Cardiology", "MBBS, DM Cardiology", ["English", "Hindi"]),
    ("Dr. Meera Iyer", "Pediatrics", "MBBS, MD Pediatrics", ["English", "Telugu"]),
    ("Dr. Arjun Nair", "Orthopedics", "MBBS, MS Orthopedics", ["English", "Hindi", "Telugu"]),
    ("Dr. Kavya Menon", "Dermatology", "MBBS, MD Dermatology", ["English", "Hindi", "Telugu"]),
]

AFTERNOON_DOCTORS = {"Dr. Vikram Singh", "Dr. Kavya Menon"}


async def seed_database(session: AsyncSession) -> bool:
    """Insert demo clinic data if not already present. Returns True if newly seeded."""
    existing = await session.scalar(select(Clinic.id).where(Clinic.name == CLINIC_NAME).limit(1))
    if existing is not None:
        return False

    clinic = Clinic(
        name=CLINIC_NAME,
        timezone="Asia/Kolkata",
        phone="+91 80 4000 1234",
        address="12 Health Avenue, Bengaluru",
        opening_time=time(8, 0),
        closing_time=time(18, 0),
        slot_minutes=30,
    )
    session.add(clinic)
    await session.flush()

    specialty_map: dict[str, Specialty] = {}
    for name, description in SPECIALTIES:
        row = Specialty(name=name, description=description)
        session.add(row)
        specialty_map[name] = row
    await session.flush()

    for name, specialty_name, qualifications, languages in DOCTORS:
        doctor = Doctor(
            clinic_id=clinic.id,
            specialty_id=specialty_map[specialty_name].id,
            name=name,
            qualifications=qualifications,
            languages=languages,
        )
        session.add(doctor)
        await session.flush()

        start = time(13, 0) if name in AFTERNOON_DOCTORS else time(9, 0)
        end = time(17, 0) if name in AFTERNOON_DOCTORS else time(13, 0)
        for weekday in range(1, 7):  # Mon–Sat
            session.add(DoctorSchedule(doctor_id=doctor.id, weekday=weekday, start_time=start, end_time=end))

    return True
