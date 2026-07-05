import re

from clinic.db import _make_reference
from clinic.orm.engine import sanitize_dsn
from clinic.prompts import MISSING_INFO, NO_CLINIC_DATA, build_instructions, greeting


def test_booking_reference_format_and_uniqueness():
    refs = {_make_reference() for _ in range(500)}
    assert len(refs) > 490  # effectively unique
    for r in list(refs)[:20]:
        assert re.fullmatch(r"AAR-[A-Z2-9]{6}", r)
        assert "0" not in r and "O" not in r and "1" not in r and "I" not in r


def test_sanitize_dsn_strips_libpq_only_params():
    dsn = "postgresql://u:p@host/db?sslmode=require&channel_binding=require"
    assert sanitize_dsn(dsn) == "postgresql://u:p@host/db"


def test_prompt_contains_mandated_phrases_per_language():
    for lang in ("en", "hi", "te"):
        text = build_instructions(
            language=lang, now_str="Monday, 01 January 2030, 09:00", clinic_summary="Test clinic."
        )
        assert MISSING_INFO[lang] in text
        assert NO_CLINIC_DATA[lang] in text


def test_english_phrases_are_verbatim():
    assert MISSING_INFO["en"] == "I don't have that information."
    assert NO_CLINIC_DATA["en"] == "No clinic data configured. Please contact support."


def test_greeting_includes_clinic_name():
    assert "Aarogya Family Clinic" in greeting("en", "Aarogya Family Clinic")
    assert greeting("hi", "X").strip() != ""
    assert greeting("te", "X").strip() != ""
