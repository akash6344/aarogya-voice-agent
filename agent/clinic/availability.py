"""Pure availability computation.

Kept free of I/O so it can be unit-tested deterministically. All datetimes are
timezone-aware. Slot start instants are compared by their absolute point in time,
so inputs may be in any timezone.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def _overlaps(start: datetime, end: datetime, block_start: datetime, block_end: datetime) -> bool:
    return start < block_end and block_start < end


def compute_available_slots(
    *,
    on_date: date,
    now: datetime,
    tz: ZoneInfo,
    schedules: list[tuple[time, time]],
    slot_minutes: int,
    blocked: list[tuple[datetime, datetime]] | None = None,
    booked_starts: set[datetime] | None = None,
    horizon_end: time | None = None,
) -> list[datetime]:
    """Return the list of bookable slot start datetimes (tz-aware, in ``tz``).

    A slot is bookable when it fits fully inside a working window, is not in the
    past, does not overlap a blocked period, and is not already booked.
    """
    blocked = blocked or []
    booked = booked_starts or set()
    booked_instants = {b.timestamp() for b in booked}
    step = timedelta(minutes=slot_minutes)

    slots: list[datetime] = []
    seen: set[float] = set()
    for window_start, window_end in schedules:
        cursor = datetime.combine(on_date, window_start, tzinfo=tz)
        end_boundary = datetime.combine(on_date, window_end, tzinfo=tz)
        if horizon_end is not None:
            end_boundary = min(end_boundary, datetime.combine(on_date, horizon_end, tzinfo=tz))
        while cursor + step <= end_boundary:
            slot_start = cursor
            slot_end = cursor + step
            cursor = slot_end
            if slot_start < now:
                continue
            instant = slot_start.timestamp()
            if instant in seen or instant in booked_instants:
                continue
            if any(_overlaps(slot_start, slot_end, bs, be) for bs, be in blocked):
                continue
            seen.add(instant)
            slots.append(slot_start)
    return sorted(slots)


def parse_date(value: str) -> date:
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()


def parse_time(value: str) -> time:
    cleaned = " ".join(value.strip().upper().replace(".", "").split())
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I %p", "%I:%M%p", "%I%p"):
        try:
            return datetime.strptime(cleaned, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized time: {value!r}")


def combine(on_date: date, at_time: time, tz: ZoneInfo) -> datetime:
    return datetime.combine(on_date, at_time, tzinfo=tz)
