import pytest

from clinic.availability import parse_time
from clinic.validators import normalize_specialty_query, patient_name_ok, patient_phone_ok


def test_normalize_specialty_aliases():
    assert normalize_specialty_query("eye doctor") == "Ophthalmology"
    assert normalize_specialty_query("dermatologist") == "Dermatology"
    assert normalize_specialty_query("Cardiology") == "Cardiology"


def test_patient_phone_rejects_missing_and_clinic_number():
    ok, msg = patient_phone_ok("", clinic_phone="+91 80 4000 1234")
    assert not ok
    assert "phone" in msg.lower()

    ok, msg = patient_phone_ok("+91 80 4000 1234", clinic_phone="+91 80 4000 1234")
    assert not ok
    assert "personal" in msg.lower()


def test_patient_phone_accepts_real_number():
    ok, msg = patient_phone_ok("+91 98765 43210", clinic_phone="+91 80 4000 1234")
    assert ok
    assert msg == ""


def test_patient_name_requires_minimum():
    ok, msg = patient_name_ok("A")
    assert not ok
    ok, msg = patient_name_ok("Akash")
    assert ok


@pytest.mark.parametrize(
    "value",
    ["10:00 AM", "15:30", "3:30 PM", "10:00AM"],
)
def test_parse_time_variants(value: str):
    parsed = parse_time(value)
    assert parsed.hour is not None


def test_is_rate_limited_detects_quota_errors():
    from livekit.agents import APIStatusError

    from clinic.llm_fallback import is_rate_limited

    assert is_rate_limited(APIStatusError("quota", status_code=429))
    assert is_rate_limited(APIStatusError("busy", status_code=503))
    assert not is_rate_limited(APIStatusError("bad request", status_code=400))
    assert not is_rate_limited(RuntimeError("network down"))


def test_build_llm_auto_with_gemini_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.0-flash-001")

    from clinic.llm_fallback import RateLimitFallbackLLM
    from clinic.providers import build_llm

    llm = build_llm()
    assert isinstance(llm, RateLimitFallbackLLM)
