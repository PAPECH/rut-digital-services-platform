export interface DashboardPeriod {
  date_from: string;
  date_to: string;
}

export interface BotSummary {
  active_users: number;
  new_users: number;
  submissions: number;
  submitters: number;
  conversion_rate: number;
  open_tickets: number;
  avg_response_seconds: number;
  avg_new_to_work_seconds: number;
  avg_work_to_done_seconds: number;
  avg_new_to_done_seconds: number;
  ai_answers: number;
  content_interactions: number;
  capability_uses: number;
  campaign_link_opens: number;
  campaign_link_unique_opens: number;
  campaign_link_repeat_opens: number;
  campaign_link_unmatched_opens: number;
}

export interface FunnelStep {
  key: string;
  label: string;
  total: number;
  unique_users: number;
}

export interface BotTrendPoint {
  day: string;
  active_users: number;
  submissions: number;
}

export interface FormMetric {
  form_id: number;
  name: string;
  opens: number;
  starts: number;
  submissions: number;
  unique_users: number;
  completion_rate: number;
  rejected_share: number;
}

export interface ContentMetric {
  category_id: number;
  content_version_id: number;
  category_name: string;
  kind: string;
  block_id: string | null;
  item_id: string | null;
  label: string;
  target_label: string | null;
  total: number;
  unique_users: number;
}

export interface CapabilityMetric {
  capability_key: string;
  view_key: string | null;
  opens: number;
  lookups: number;
  successful_lookups: number;
  subscription_changes: number;
  unique_users: number;
}

export interface TicketTrendPoint {
  day: string;
  incoming: number;
  answered: number;
}

export interface CampaignLinkMetric {
  campaign_link_id: number;
  code: string;
  campaign: string;
  source: string;
  placement: string;
  target: "bot" | "webapp";
  opens: number;
  unique_opens: number;
}

export interface BotDashboard {
  generated_at: string;
  period: DashboardPeriod;
  summary: BotSummary;
  previous_summary: BotSummary;
  funnel: FunnelStep[];
  trend: BotTrendPoint[];
  forms: FormMetric[];
  content: ContentMetric[];
  capabilities: CapabilityMetric[];
  tickets_trend: TicketTrendPoint[];
  campaign_links: CampaignLinkMetric[];
}

export interface PlatformSummary {
  bots: number;
  active_users: number;
  new_people: number;
  new_memberships: number;
  cross_bot_users: number;
  submissions: number;
  submitters: number;
  conversion_rate: number;
  open_tickets: number;
  avg_response_seconds: number;
  avg_new_to_done_seconds: number;
  content_interactions: number;
  capability_uses: number;
  campaign_link_opens: number;
  campaign_link_unique_opens: number;
  campaign_link_repeat_opens: number;
  campaign_link_unmatched_opens: number;
}

export interface BotComparison {
  bot_id: number;
  slug: string;
  name: string;
  active_users: number;
  new_users: number;
  submissions: number;
  submitters: number;
  conversion_rate: number;
  content_interactions: number;
  capability_uses: number;
  open_tickets: number;
  avg_response_seconds: number;
  avg_new_to_done_seconds: number;
  previous: BotSummary;
  campaign_link_opens: number;
  campaign_link_unique_opens: number;
  campaign_link_repeat_opens: number;
  campaign_link_unmatched_opens: number;
}

export interface PlatformTrendPoint {
  day: string;
  bot_id: number;
  bot_name: string;
  active_users: number;
  submissions: number;
}

export interface PlatformDashboard {
  generated_at: string;
  period: DashboardPeriod;
  summary: PlatformSummary;
  previous_summary: PlatformSummary;
  bots: BotComparison[];
  trend: PlatformTrendPoint[];
}

export type DashboardScope = "platform" | "bot";

export interface DashboardFilters {
  days: 7 | 30 | 90;
  dateFrom: string;
  dateTo: string;
}
