"""Input validation helpers for booking tools."""
from __future__ import annotations

import re

_SPECIALTY_ALIASES: dict[str, str] = {
    "eye": "Ophthalmology",
    "eye doctor": "Ophthalmology",
    "ophthalmologist": "Ophthalmology",
    "skin": "Dermatology",
    "dermatologist": "Dermatology",
    "derma": "Dermatology",
    "heart": "Cardiology",
    "cardiologist": "Cardiology",
    "child": "Pediatrics",
    "children": "Pediatrics",
    "pediatrician": "Pediatrics",
    "bone": "Orthopedics",
    "orthopedic": "Orthopedics",
    "orthopedist": "Orthopedics",
    "general": "General Medicine",
    "gp": "General Medicine",
    "general physician": "General Medicine",
}


def normalize_specialty_query(value: str) -> str:
    key = " ".join(value.strip().lower().split())
    return _SPECIALTY_ALIASES.get(key, value.strip())


def patient_phone_ok(phone: str, *, clinic_phone: str | None = None) -> tuple[bool, str]:
    """Return (ok, spoken_error_message). Reject missing, too short, or clinic numbers."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) < 10:
        return False, "I still need your mobile phone number before I can book. What number can we reach you on?"
    if len(set(digits)) <= 2:
        return False, "That doesn't sound like a phone number. Could you tell me your mobile number again?"
    if clinic_phone:
        clinic_digits = re.sub(r"\D", "", clinic_phone)
        if digits == clinic_digits or digits.endswith(clinic_digits[-10:]):
            return (
                False,
                "I need your personal phone number, not the clinic number. What's the best number to reach you?",
            )
    return True, ""


def patient_name_ok(name: str) -> tuple[bool, str]:
    cleaned = " ".join((name or "").split())
    if len(cleaned) < 2:
        return False, "I still need your name before I can book. What name should I put on the appointment?"
    return True, ""
