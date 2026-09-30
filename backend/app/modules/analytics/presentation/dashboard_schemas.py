from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DashboardModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DashboardPeriodResponse(DashboardModel):
    date_from: date
    date_to: date


class BotSummaryResponse(DashboardModel):
    active_users: int
    new_users: int
    submissions: int
    submitters: int
    conversion_rate: float
    open_tickets: int
    avg_response_seconds: int
    avg_new_to_work_seconds: int
    avg_work_to_done_seconds: int
    avg_new_to_done_seconds: int
    ai_answers: int
    content_interactions: int
    capability_uses: int
    campaign_link_opens: int
    campaign_link_unique_opens: int
    campaign_link_repeat_opens: int
    campaign_link_unmatched_opens: int


class FunnelStepResponse(DashboardModel):
    key: str
    label: str
    total: int
    unique_users: int


class BotTrendPointResponse(DashboardModel):
    day: date
    active_users: int
    submissions: int


class FormMetricResponse(DashboardModel):
    form_id: int
    name: str
    opens: int
    starts: int
    submissions: int
    unique_users: int
    completion_rate: float
    rejected_share: float


class ContentMetricResponse(DashboardModel):
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


class CapabilityMetricResponse(DashboardModel):
    capability_key: str
    view_key: str | None
    opens: int
    lookups: int
    successful_lookups: int
    subscription_changes: int
    unique_users: int


class TicketTrendPointResponse(DashboardModel):
    day: date
    incoming: int
    answered: int


class CampaignLinkMetricResponse(DashboardModel):
    campaign_link_id: int
    code: str
    campaign: str
    source: str
    placement: str
    target: str
    opens: int
    unique_opens: int


class BotDashboardResponse(DashboardModel):
    generated_at: datetime
    period: DashboardPeriodResponse
    summary: BotSummaryResponse
    previous_summary: BotSummaryResponse
    funnel: list[FunnelStepResponse]
    trend: list[BotTrendPointResponse]
    forms: list[FormMetricResponse]
    content: list[ContentMetricResponse]
    capabilities: list[CapabilityMetricResponse]
    tickets_trend: list[TicketTrendPointResponse]
    campaign_links: list[CampaignLinkMetricResponse]


class PlatformSummaryResponse(DashboardModel):
    bots: int
    active_users: int
    new_people: int
    new_memberships: int
    cross_bot_users: int
    submissions: int
    submitters: int
    conversion_rate: float
    open_tickets: int
    avg_response_seconds: int
    avg_new_to_done_seconds: int
    content_interactions: int
    capability_uses: int
    campaign_link_opens: int
    campaign_link_unique_opens: int
    campaign_link_repeat_opens: int
    campaign_link_unmatched_opens: int


class BotComparisonResponse(DashboardModel):
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
    avg_new_to_done_seconds: int
    previous: BotSummaryResponse
    campaign_link_opens: int
    campaign_link_unique_opens: int
    campaign_link_repeat_opens: int
    campaign_link_unmatched_opens: int


class PlatformTrendPointResponse(DashboardModel):
    day: date
    bot_id: int
    bot_name: str
    active_users: int
    submissions: int


class PlatformDashboardResponse(DashboardModel):
    generated_at: datetime
    period: DashboardPeriodResponse
    summary: PlatformSummaryResponse
    previous_summary: PlatformSummaryResponse
    bots: list[BotComparisonResponse]
    trend: list[PlatformTrendPointResponse]
