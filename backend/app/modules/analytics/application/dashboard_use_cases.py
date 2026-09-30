from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ..domain.dashboard import BotDashboard, DashboardPeriod, PlatformDashboard
from .ports import DashboardRepository

MOSCOW = ZoneInfo("Europe/Moscow")


class InvalidDashboardPeriod(ValueError):
    pass


def resolve_period(
    *,
    days: int,
    date_from: date | None,
    date_to: date | None,
    now: datetime | None = None,
) -> tuple[DashboardPeriod, DashboardPeriod]:
    current = (now or datetime.now(UTC)).astimezone(MOSCOW)
    if (date_from is None) != (date_to is None):
        raise InvalidDashboardPeriod("Both date_from and date_to are required")
    if date_from is not None and date_to is not None:
        if date_to < date_from:
            raise InvalidDashboardPeriod("date_to must not be earlier than date_from")
        if (date_to - date_from).days > 365:
            raise InvalidDashboardPeriod("Dashboard period cannot exceed 366 days")
        start_local = datetime.combine(date_from, time.min, tzinfo=MOSCOW)
        end_local = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=MOSCOW)
    else:
        if days < 1 or days > 365:
            raise InvalidDashboardPeriod("days must be between 1 and 365")
        end_local = current
        start_local = end_local - timedelta(days=days)
        date_from = start_local.date()
        date_to = end_local.date()
    duration = end_local - start_local
    previous_start_local = start_local - duration
    return (
        DashboardPeriod(
            start=start_local.astimezone(UTC),
            end=end_local.astimezone(UTC),
            date_from=date_from,
            date_to=date_to,
        ),
        DashboardPeriod(
            start=previous_start_local.astimezone(UTC),
            end=start_local.astimezone(UTC),
            date_from=previous_start_local.date(),
            date_to=(start_local - timedelta(microseconds=1)).date(),
        ),
    )


class GetBotDashboard:
    def __init__(self, repository: DashboardRepository) -> None:
        self._repository = repository

    def execute(
        self,
        bot_instance_id: int,
        period: DashboardPeriod,
        previous_period: DashboardPeriod,
    ) -> BotDashboard:
        return self._repository.get_bot_dashboard(bot_instance_id, period, previous_period)


class GetPlatformDashboard:
    def __init__(self, repository: DashboardRepository) -> None:
        self._repository = repository

    def execute(
        self,
        period: DashboardPeriod,
        previous_period: DashboardPeriod,
        *,
        include_inactive: bool,
    ) -> PlatformDashboard:
        return self._repository.get_platform_dashboard(
            period,
            previous_period,
            include_inactive=include_inactive,
        )
