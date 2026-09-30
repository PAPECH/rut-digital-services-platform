from __future__ import annotations

from datetime import datetime, timedelta

# Mon-Fri only -- RF public holidays are not accounted for (see docs/tasks/064, "RF
# public-holiday-aware business-day counting" under Scope and non-goals). This only ever
# makes the real window longer than the statutory 10 business days, never shorter.
_WEEKEND = (5, 6)  # Saturday, Sunday


def add_business_days(start: datetime, days: int) -> datetime:
    if days < 0:
        raise ValueError("days must be non-negative")
    cursor = start
    remaining = days
    while remaining > 0:
        cursor += timedelta(days=1)
        if cursor.weekday() not in _WEEKEND:
            remaining -= 1
    return cursor
