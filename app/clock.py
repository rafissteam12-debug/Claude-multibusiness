"""Single source of "now" so tests can time-travel (retention, token expiry, usage month)."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_offset_seconds = 0.0
BERLIN = ZoneInfo("Europe/Berlin")


def now() -> float:
    """Epoch seconds (UTC), shifted by the test offset."""
    return time.time() + _offset_seconds


def travel(seconds: float) -> None:
    """Move the clock forward (tests only)."""
    global _offset_seconds
    _offset_seconds += seconds


def reset() -> None:
    global _offset_seconds
    _offset_seconds = 0.0


def month_key(ts: float | None = None) -> str:
    """Calendar month in German time, e.g. '2026-10'."""
    return datetime.fromtimestamp(now() if ts is None else ts, BERLIN).strftime("%Y-%m")


def iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def de_datetime(ts: float | None) -> str:
    if ts is None:
        return ""
    return datetime.fromtimestamp(ts, BERLIN).strftime("%d.%m.%Y, %H:%M Uhr")


MONTHS_DE = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober",
             "November", "Dezember")


def de_long(ts: float | None) -> str:
    """German local time in words, e.g. '2. November, 01:37 Uhr' (year added if not the current one)."""
    if ts is None:
        return ""
    d = datetime.fromtimestamp(ts, BERLIN)
    year = "" if d.year == datetime.fromtimestamp(now(), BERLIN).year else f" {d.year}"
    return f"{d.day}. {MONTHS_DE[d.month - 1]}{year}, {d:%H:%M} Uhr"
