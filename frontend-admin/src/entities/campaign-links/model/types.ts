export type CampaignLinkTarget = "bot" | "webapp";

export interface CampaignLink {
  id: number;
  bot_instance_id: number;
  code: string;
  campaign: string;
  source: string;
  placement: string;
  target: CampaignLinkTarget;
  created_at: string;
  open_count: number;
  unique_open_count: number;
  /** Mirrors `open_count` exactly (kept for backward compatibility, same meaning per target). */
  first_open_count: number;
  /** Always 0 for a `target: webapp` row -- meaningful only for `target: bot`. */
  repeat_open_count: number;
  last_opened_at: string | null;
  bot_username: string | null;
  deep_link: string;
}

export interface CampaignLinkCreateInput {
  code: string;
  campaign: string;
  source: string;
  placement: string;
  target: CampaignLinkTarget;
}

export type UnmatchedCampaignLinkSource = "bot_started" | "bot_repeat" | "webapp";

export interface UnmatchedCampaignLink {
  code: string;
  event_source: UnmatchedCampaignLinkSource;
  hit_count: number;
  last_seen_at: string;
}
