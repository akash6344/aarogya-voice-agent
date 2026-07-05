"""Clinic scheduling domain."""
from .models import (
    Appointment,
    BookingError,
    Clinic,
    Doctor,
    Slot,
    SlotTakenError,
    Specialty,
)

__all__ = [
    "Appointment",
    "BookingError",
    "Clinic",
    "Doctor",
    "Slot",
    "SlotTakenError",
    "Specialty",
]
