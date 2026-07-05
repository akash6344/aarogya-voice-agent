from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from clinic.availability import compute_available_slots, parse_date, parse_time

TZ = ZoneInfo("Asia/Kolkata")


def _dt(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=TZ)


def test_generates_back_to_back_slots_within_window():
    slots = compute_available_slots(
        on_date=date(2030, 1, 7),  # a Monday, far future so nothing is in the past
        now=_dt(2030, 1, 1, 0),
        tz=TZ,
        schedules=[(time(9, 0), time(11, 0))],
        slot_minutes=30,
    )
    assert [s.strftime("%H:%M") for s in slots] == ["09:00", "09:30", "10:00", "10:30"]


def test_partial_trailing_slot_is_excluded():
    slots = compute_available_slots(
        on_date=date(2030, 1, 7),
        now=_dt(2030, 1, 1, 0),
        tz=TZ,
        schedules=[(time(9, 0), time(10, 20))],  # only 09:00 and 09:30 fit fully
        slot_minutes=30,
    )
    assert [s.strftime("%H:%M") for s in slots] == ["09:00", "09:30"]


def test_past_slots_removed_for_today():
    slots = compute_available_slots(
        on_date=date(2030, 1, 7),
        now=_dt(2030, 1, 7, 9, 45),  # mid-morning
        tz=TZ,
        schedules=[(time(9, 0), time(11, 0))],
        slot_minutes=30,
    )
    assert [s.strftime("%H:%M") for s in slots] == ["10:00", "10:30"]


def test_booked_slot_excluded():
    slots = compute_available_slots(
        on_date=date(2030, 1, 7),
        now=_dt(2030, 1, 1, 0),
        tz=TZ,
        schedules=[(time(9, 0), time(11, 0))],
        slot_minutes=30,
        booked_starts={_dt(2030, 1, 7, 9, 30)},
    )
    assert [s.strftime("%H:%M") for s in slots] == ["09:00", "10:00", "10:30"]


def test_booked_slot_excluded_across_timezones():
    # Same instant as 09:30 IST, expressed in UTC (04:00Z). Must still be excluded.
    booked_utc = datetime(2030, 1, 7, 4, 0, tzinfo=ZoneInfo("UTC"))
    slots = compute_available_slots(
        on_date=date(2030, 1, 7),
        now=_dt(2030, 1, 1, 0),
        tz=TZ,
        schedules=[(time(9, 0), time(11, 0))],
        slot_minutes=30,
        booked_starts={booked_utc},
    )
    assert "09:30" not in [s.strftime("%H:%M") for s in slots]


def test_blocked_period_excludes_overlapping_slots():
    slots = compute_available_slots(
        on_date=date(2030, 1, 7),
        now=_dt(2030, 1, 1, 0),
        tz=TZ,
        schedules=[(time(9, 0), time(11, 0))],
        slot_minutes=30,
        blocked=[(_dt(2030, 1, 7, 9, 15), _dt(2030, 1, 7, 10, 15))],
    )
    # 09:00-09:30 overlaps block, 09:30, 10:00 overlap; only 10:30 survives
    assert [s.strftime("%H:%M") for s in slots] == ["10:30"]


def test_no_schedule_means_no_slots():
    assert compute_available_slots(
        on_date=date(2030, 1, 7),
        now=_dt(2030, 1, 1, 0),
        tz=TZ,
        schedules=[],
        slot_minutes=30,
    ) == []


@pytest.mark.parametrize(
    "value,expected",
    [("09:00", time(9, 0)), ("9:30 AM", time(9, 30)), ("2:15 PM", time(14, 15)), ("14:45", time(14, 45))],
)
def test_parse_time_accepts_common_formats(value, expected):
    assert parse_time(value) == expected


def test_parse_date():
    assert parse_date("2026-07-04") == date(2026, 7, 4)


def test_parse_time_rejects_garbage():
    with pytest.raises(ValueError):
        parse_time("later today")
