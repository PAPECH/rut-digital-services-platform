from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class DashboardPeriod:
    start: datetime
    end: datetime
    date_from: date
    date_to: date


@dataclass(frozen=True, slots=True)
class BotSummary:
    active_users: int = 0
    new_users: int = 0
    submissions: int = 0
    submitters: int = 0
    conversion_rate: float = 0
    open_tickets: int = 0
    avg_response_seconds: int = 0
    avg_new_to_work_seconds: int = 0
    avg_work_to_done_seconds: int = 0
    avg_new_to_done_seconds: int = 0
    ai_answers: int = 0
    content_interactions: int = 0
    capability_uses: int = 0
    campaign_link_opens: int = 0
    campaign_link_unique_opens: int = 0
    # Lifetime total: the underlying counter has no per-open timestamp.
    campaign_link_repeat_opens: int = 0
    campaign_link_unmatched_opens: int = 0


@dataclass(frozen=True, slots=True)
class FunnelStep:
    key: str
    label: str
    total: int
    unique_users: int


@dataclass(frozen=True, slots=True)
class BotTrendPoint:
    day: date
    active_users: int = 0
    submissions: int = 0


@dataclass(frozen=True, slots=True)
class FormMetric:
    form_id: int
    name: str
    opens: int
    starts: int
    submissions: int
    unique_users: int
    completion_rate: float
    rejected_share: float


@dataclass(frozen=True, slots=True)
class ContentMetric:
    category_id: int
    content_version_id: int
    category_name: str
    kind: str
    block_id: str | None
    item_id: str | None
    label: str
    target_label: str | None
    total: int
    unique_users: int


@dataclass(frozen=True, slots=True)
class CapabilityMetric:
    capability_key: str
    view_key: str | None
    opens: int
    lookups: int
    successful_lookups: int
    subscription_changes: int
    unique_users: int


@dataclass(frozen=True, slots=True)
class TicketTrendPoint:
    day: date
    incoming: int = 0
    answered: int = 0


@dataclass(frozen=True, slots=True)
class CampaignLinkMetric:
    campaign_link_id: int
    code: str
    campaign: str
    source: str
    placement: str
    target: str
    opens: int
    unique_opens: int


@dataclass(frozen=True, slots=True)
class BotDashboard:
    generated_at: datetime
    period: DashboardPeriod
    summary: BotSummary
    previous_summary: BotSummary
    funnel: tuple[FunnelStep, ...]
    trend: tuple[BotTrendPoint, ...]
    forms: tuple[FormMetric, ...]
    content: tuple[ContentMetric, ...]
    capabilities: tuple[CapabilityMetric, ...]
    tickets_trend: tuple[TicketTrendPoint, ...]
    campaign_links: tuple[CampaignLinkMetric, ...] = ()


@dataclass(frozen=True, slots=True)
class PlatformSummary:
    bots: int = 0
    active_users: int = 0
    new_people: int = 0
    new_memberships: int = 0
    cross_bot_users: int = 0
    submissions: int = 0
    submitters: int = 0
    conversion_rate: float = 0
    open_tickets: int = 0
    avg_response_seconds: int = 0
    avg_new_to_done_seconds: int = 0
    content_interactions: int = 0
    capability_uses: int = 0
    campaign_link_opens: int = 0
    campaign_link_unique_opens: int = 0
    campaign_link_repeat_opens: int = 0
    campaign_link_unmatched_opens: int = 0


@dataclass(frozen=True, slots=True)
class BotComparison:
    bot_id: int
    slug: str
    name: str
    active_users: int
    new_users: int
    submissions: int
    submitters: int
    conversion_rate: float
    content_interactions: int
    capability_uses: int
    open_tickets: int
    avg_response_seconds: int
    previous: BotSummary
    avg_new_to_done_seconds: int = 0
    campaign_link_opens: int = 0
    campaign_link_unique_opens: int = 0
    campaign_link_repeat_opens: int = 0
    campaign_link_unmatched_opens: int = 0


@dataclass(frozen=True, slots=True)
class PlatformTrendPoint:
    day: date
    bot_id: int
    bot_name: str
    active_users: int = 0
    submissions: int = 0


@dataclass(frozen=True, slots=True)
class PlatformDashboard:
    generated_at: datetime
    period: DashboardPeriod
    summary: PlatformSummary
    previous_summary: PlatformSummary
    bots: tuple[BotComparison, ...]
    trend: tuple[PlatformTrendPoint, ...]
