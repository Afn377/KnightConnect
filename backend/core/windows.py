"""Availability windows on specific event days.

A window is {"date": "YYYY-MM-DD", "start": "HH:MM" | None, "end": "HH:MM" | None};
no start and end means the whole day. Times are campus local time.
"""

import re
from datetime import date

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.dateparse import parse_date

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
WHOLE_DAY = (0, 24 * 60)


def _minutes(value):
    match = TIME_PATTERN.match(value or "")
    if not match:
        raise ValidationError("Times must use 24-hour HH:MM.")
    return int(match.group(1)) * 60 + int(match.group(2))


def normalize_windows(value):
    """Validate a list of windows and return it with every key present."""
    if not isinstance(value, list):
        raise ValidationError("Availability must be a list of day windows.")
    normalized, seen = [], set()
    for window in value:
        if not isinstance(window, dict) or "date" not in window or set(window) - {"date", "start", "end"}:
            raise ValidationError("Each window needs a date and optional start and end times.")
        day = parse_date(window["date"]) if isinstance(window["date"], str) else None
        if day is None:
            raise ValidationError("Dates must use YYYY-MM-DD.")
        start, end = window.get("start"), window.get("end")
        if (start is None) != (end is None):
            raise ValidationError("Give both a start and an end time, or neither for the whole day.")
        if start is not None and _minutes(start) >= _minutes(end):
            raise ValidationError("A window's start must be before its end.")
        key = (day, start, end)
        if key in seen:
            raise ValidationError("Windows must not repeat.")
        seen.add(key)
        normalized.append({"date": day.isoformat(), "start": start, "end": end})
    return normalized


def validate_windows(value):
    normalize_windows(value)


def window_ranges(windows):
    """Map each date to its (start_minute, end_minute) ranges."""
    ranges = {}
    for window in windows:
        span = WHOLE_DAY if window.get("start") is None else (_minutes(window["start"]), _minutes(window["end"]))
        ranges.setdefault(date.fromisoformat(window["date"]), []).append(span)
    return ranges


def event_dates(event):
    first = timezone.localtime(event.starts_at).date()
    last = timezone.localtime(event.ends_at).date()
    return [date.fromordinal(day) for day in range(first.toordinal(), last.toordinal() + 1)]
