"""Picks the active `ScheduleHierarchyProvider` implementation.

The only switch point: flip `settings.RUT_SCHEDULE_PROVIDER` ("miit_web" -> "oracle") once Oracle
credentials are configured (see `.env.example`) -- every consumer (the nightly sync worker) goes
through this factory instead of instantiating a provider class directly, so the switch takes
effect everywhere at once.
"""

from __future__ import annotations

from .....core.config import settings
from .oracle_provider import OracleTimetableProvider
from .provider import MiitTimetableProvider


def get_schedule_provider():
    if settings.RUT_SCHEDULE_PROVIDER == "oracle":
        return OracleTimetableProvider()
    return MiitTimetableProvider()
