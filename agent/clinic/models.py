"""Domain models for the clinic scheduling system."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class Clinic:
    id: str
    name: str
    timezone: str
    phone: str | None
    address: str | None
    opening_time: time
    closing_time: time
    slot_minutes: int


@dataclass(frozen=True)
class Specialty:
    name: str
    description: str | None


@dataclass(frozen=True)
class Doctor:
    id: str
    name: str
    specialty: str
    qualifications: str | None
    languages: tuple[str, ...]


@dataclass(frozen=True)
class Slot:
    doctor_id: str
    doctor_name: str
    specialty: str
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class Appointment:
    booking_reference: str
    doctor_name: str
    specialty: str
    patient_name: str
    phone: str
    starts_at: datetime
    ends_at: datetime
    status: str


class BookingError(Exception):
    """Raised for expected, user-facing booking failures."""


class SlotTakenError(BookingError):
    """Raised when a slot was taken concurrently (double-booking guard tripped)."""
