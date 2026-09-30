from typing import Protocol

from ..domain.dashboard import BotDashboard, DashboardPeriod, PlatformDashboard
from ..domain.events import AnalyticsEvent


class AnalyticsEventRepository(Protocol):
    def validate_context(self, event: AnalyticsEvent) -> None: ...

    def add(self, event: AnalyticsEvent) -> bool: ...


class DashboardRepository(Protocol):
    def get_bot_dashboard(
        self,
        bot_instance_id: int,
        period: DashboardPeriod,
        previous_period: DashboardPeriod,
    ) -> BotDashboard: ...

    def get_platform_dashboard(
        self,
        period: DashboardPeriod,
        previous_period: DashboardPeriod,
        *,
        include_inactive: bool,
    ) -> PlatformDashboard: ...
