import type { ContentIconName } from "@/entities/content/model/contentIcons";

export type SubmissionStatus = "new" | "in_work" | "rejected" | "done";

export interface Profile {
  id: number;
  user_id: string;
  system: string;
  first_name: string | null;
  last_name: string | null;
  patronymic: string | null;
  username: string | null;
  phone: string | null;
  phone_verified: boolean;
  email: string | null;
  photo_url: string | null;
  language_code: string | null;
  birth_date: string | null;
  study_group: string | null;
  rut_personnel_number: string | null;
  job_title: string | null;
  structural_unit: string | null;
  shared_data: Record<string, unknown>;
  local_data: Record<string, unknown>;
  ban_chat: boolean;
  ban_chat_reason: string | null;
  ban_forms: boolean;
  ban_forms_reason: string | null;
  ban_app: boolean;
  ban_app_reason: string | null;
  // Task 064 -- drives the full-screen consent gate in App.tsx exactly like ban_app does.
  consent_is_active: boolean;
  consent_given_at: string | null;
  consent_revoked_at: string | null;
  consent_deletion_due_at: string | null;
  consent_policy_url: string;
}

export type MaintenanceMode =
  "off" | "informational" | "read_only" | "full_stop";

export interface MaintenancePolicy {
  scope_key: string;
  bot_instance_id: number | null;
  mode: MaintenanceMode;
  title: string;
  message: string;
  starts_at: string | null;
  ends_at: string | null;
  retry_after_seconds: number | null;
  allow_admin: boolean;
}

export interface AppManifest {
  bot: {
    id: number;
    slug: string;
    name: string;
    description: string | null;
    branding: Record<string, unknown>;
    settings: BotSettings;
    profile_schema: ProfileFieldDefinition[];
  };
  maintenance: MaintenancePolicy | null;
  capabilities: PublicCapability[];
}

export type BottomNavigationIcon = ContentIconName;

export interface BottomNavigationItem {
  target: "category" | "submission_history" | "form_catalog";
  category_slug: string | null;
  label: string;
  icon: BottomNavigationIcon;
}

export interface BotSettings {
  bottom_navigation: {
    custom_items: BottomNavigationItem[];
  };
  submission_table: {
    profile_fields: string[];
  };
  profile: {
    enabled: boolean;
  };
}

export interface CapabilityView {
  key: string;
  title: string;
  subtitle: string | null;
  icon: string;
  path: string;
  requires_complete_profile: boolean;
}

export interface PublicCapability {
  installation_id: number;
  key: string;
  version: string;
  views: CapabilityView[];
  public_config: Record<string, unknown>;
}

export interface ProfileFieldDefinition {
  key: string;
  label: string;
  type: "string" | "email" | "phone" | "boolean" | "date" | "number" | "select";
  required: boolean;
  shared?: boolean;
  options?: string[] | null;
}

export interface StatusHistoryItem {
  id: number;
  from_status: SubmissionStatus | null;
  to_status: SubmissionStatus;
  changed_at: string;
  comment: string | null;
}

export interface Submission {
  id: number;
  form_template_id: number;
  form_version_id: number;
  user_id: number;
  values: Record<string, unknown>;
  field_labels: Record<string, string>;
  form_snapshot: Record<string, unknown>;
  profile_snapshot: Record<string, unknown>;
  status: SubmissionStatus;
  created_at: string;
  closed_at: string | null;
  history?: StatusHistoryItem[];
  form_name?: string | null;
}

export interface SubmissionAttachment {
  id: number;
  field_key: string;
  name: string;
  mime: string;
  size_bytes: number;
  preview_url: string;
  download_url: string;
}

export interface MonitoringLookup {
  request_number: string;
  status: string | null;
  checked_at: string | null;
  is_subscribed: boolean;
}

export interface MonitoringSubscription {
  request_number: string | null;
  is_active: boolean;
  last_status: string | null;
  checked_at: string | null;
}
