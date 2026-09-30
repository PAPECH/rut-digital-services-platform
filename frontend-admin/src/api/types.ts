import type { ContentIconName } from "@/entities/content/model/contentIcons";

export type System = "max" | "beavers";
export type AdminRole = "employee" | "admin" | "platform_admin";
export type FieldType = "string" | "number" | "date" | "checkbox";
export type SubmissionStatus = "new" | "in_work" | "rejected" | "done";

export interface TicketsOverview {
  open_count: number;
  unread_count: number;
}

export interface AdminProfile {
  id: number;
  max_user_id: string;
  full_name: string;
  role: AdminRole;
  is_active: boolean;
}

export interface BotInstance {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  is_active: boolean;
  order: number;
  branding: Record<string, unknown>;
  settings: BotSettings;
  profile_schema: ProfileFieldDefinition[];
  deleted_at: string | null;
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
  chat: {
    student_text_enabled: boolean;
  };
  knowledge_base: {
    auto_answer_threshold: number | null;
    candidate_min_threshold: number | null;
    max_candidates: number | null;
  };
  profile: {
    enabled: boolean;
  };
}

export interface BotRuntime {
  bot_instance_id: number;
  credential_source: "environment" | "managed" | null;
  credential_env_key: string | null;
  mode: "polling" | "webhook";
  bot_token_configured: boolean;
  token_configured: boolean;
  status: "online" | "offline" | "error" | "not_connected";
  last_seen_at: string | null;
  username: string | null;
  max_bot_id: string | null;
  runtime_version: string | null;
  last_error_code: string | null;
}

export interface ProfileFieldDefinition {
  key: string;
  label: string;
  type: "string" | "email" | "phone" | "boolean" | "date" | "number" | "select";
  required: boolean;
  shared?: boolean;
  options?: string[] | null;
}

export interface CapabilityView {
  key: string;
  title: string;
  subtitle: string | null;
  icon: string;
  path: string;
  requires_complete_profile: boolean;
}

export interface CapabilityInstallation {
  id: number | null;
  bot_instance_id: number;
  capability_key: string;
  version: string;
  name: string;
  description: string;
  admin_editor_key: string;
  is_enabled: boolean;
  order: number;
  config: Record<string, unknown>;
  config_revision: number;
  last_health_status: "unconfigured" | "unknown" | "healthy" | "degraded";
  last_health_at: string | null;
  last_health_error_code: string | null;
  views: CapabilityView[];
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

export interface FormField {
  id: number;
  label: string;
  type: FieldType;
  regexp: string | null;
  min_value: string | null;
  max_value: string | null;
  default_value: string | null;
  is_active: boolean;
  is_required: boolean;
  order: number;
  profile_key: string | null;
  meta: Record<string, unknown> | null;
}

export interface FormTemplate {
  id: number;
  name: string;
  description: string | null;
  is_active: boolean;
  order: number;
  reply_on_accept: string | null;
  created_at: string;
  updated_at: string;
}

export interface FormTemplateDetailed extends FormTemplate {
  fields: FormField[];
}

export interface Submitter {
  id: number;
  first_name: string | null;
  last_name: string | null;
  patronymic: string | null;
  username: string | null;
  photo_url: string | null;
  user_id: string | null;
  system: string | null;
  birth_date: string | null;
  study_group: string | null;
  phone: string | null;
  phone_verified: boolean;
  email: string | null;
}

export interface StatusHistoryItem {
  id: number;
  from_status: SubmissionStatus | null;
  to_status: SubmissionStatus;
  changed_by: number | null;
  changed_at: string;
  comment: string | null;
}

export interface Submission {
  id: number;
  form_template_id: number;
  form_version_id: number;
  user_id: number;
  values: Record<string, unknown>;
  values_en?: Record<string, unknown> | null;
  field_labels: Record<string, string>;
  form_snapshot: Record<string, unknown>;
  profile_snapshot: Record<string, unknown>;
  status: SubmissionStatus;
  created_at: string;
  taken_at: string | null;
  closed_at: string | null;
  assignee_admin_id: number | null;
  history?: StatusHistoryItem[];
  submitter?: Submitter | null;
  form_name?: string | null;
  appointment?: SubmissionAppointment | null;
}

export interface SubmissionAppointment {
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  location: string;
}

export interface SubmissionAppointmentSlot {
  starts_at: string;
  submission_id: number;
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

export interface ConversationItem {
  user_id: number;
  max_user_id: string;
  first_name: string | null;
  last_name: string | null;
  username: string | null;
  photo_url: string | null;
  system: System;
  last_message_text: string | null;
  last_message_at: string | null;
  unread_count: number;
  has_open_ticket: boolean;
  is_favorite: boolean;
  my_favorite: boolean;
  staff_requested: boolean;
}

export interface AttachmentRef {
  id?: number;
  url: string;
  name?: string | null;
  mime?: string | null;
  size?: number | null;
}

// Отражает backend MessageAiClassificationEnum (backend/app/modules/knowledge_base/
// domain/entities.py) — единственный источник значений по обе стороны, чтобы строки
// не расходились между backend и frontend-admin.
export type MessageAiClassification =
  | "empty"
  | "certificate"
  | "payment"
  | "dorm"
  | "general"
  | "kb_staff_requested_text"
  | "kb_auto"
  | "kb_candidates"
  | "kb_no_match"
  | "kb_staff_requested"
  | "kb_selected"
  | "legacy_unknown";

// Синтетический маркер «студент нажал кнопку „Позвать сотрудника“» (ai_callback/
// call_staff) — рендерится как системная строка, а не обычный пузырь чата.
// kb_staff_requested_text (эскалация по тексту) сюда НЕ входит: это настоящий текст
// студента, его нельзя прятать так же, как синтетический маркер.
export const KB_STAFF_REQUESTED_MARKER: MessageAiClassification = "kb_staff_requested";

export interface MessageItem {
  id: number;
  user_id: number;
  system: System;
  direction: "in" | "out";
  text: string | null;
  attachments: AttachmentRef[] | null;
  is_ai_answered: boolean;
  ai_classification: MessageAiClassification | null;
  kb_document_id: number | null;
  replied_by_admin_id: number | null;
  replied_by_admin_name: string | null;
  created_at: string;
}

export interface CampaignSource {
  code: string;
  campaign: string;
  source: string;
  placement: string;
  target: "bot" | "webapp";
}

export interface UserSummary {
  id: number;
  user_id: string;
  system: System;
  first_name: string | null;
  last_name: string | null;
  patronymic: string | null;
  username: string | null;
  photo_url: string | null;
  phone: string | null;
  phone_verified: boolean;
  email: string | null;
  birth_date: string | null;
  study_group: string | null;
  job_title: string | null;
  structural_unit: string | null;
  ban_chat: boolean;
  ban_chat_reason: string | null;
  ban_forms: boolean;
  ban_forms_reason: string | null;
  ban_app: boolean;
  ban_app_reason: string | null;
  created_at: string;
  campaign_source: CampaignSource | null;
  // Task 064 -- read-only, same permission as the rest of this card.
  consent_given_at: string | null;
  consent_revoked_at: string | null;
  consent_deletion_due_at: string | null;
}

export interface StatsPeriod {
  date_from: string;
  date_to: string;
}

export interface StatsKpi {
  total_submissions: number;

  avg_new_to_work_seconds: number;
  avg_work_to_done_seconds: number;

  rejected_share: number;

  users_total: number;
  users_with_submission: number;
  conversion_rate: number;
}

export interface StatsFormItem {
  form_id: number;
  name: string;
  count: number;
}

export interface StatsForms {
  all: StatsFormItem[];
  new_users: StatsFormItem[];
}

export type ActionType =
  | "faq_open"
  | "abiture_search"
  | "navigator_open"
  | "submit_phone"
  | "submit_form";

export interface StatsActionItem {
  action_type: ActionType;
  count: number;
}

export interface StatsActions {
  mode: "all" | "unique";
  items: StatsActionItem[];
}

export interface StatsTicket {
  open: number;
  new: number;
  closed: number;
  avg_response_seconds: number;
  ai_answers: number;
}

export interface StatsTimeseriesItem {
  day: string | null;
  count: number;
}

export interface StatsTicketTimeseriesItem {
  day: string;
  new: number;
  closed: number;
}

export interface StatsActionTimeseriesItem {
  day: string;
  action_type: ActionType;
  count: number;
}

export interface StatsFilters {
  days?: number;
  date_from?: string;
  date_to?: string;
  action_mode: "all" | "unique";
}

export interface StatsOverview {
  period: StatsPeriod;

  kpi: StatsKpi;

  forms: StatsForms;

  actions: StatsActions;

  tickets: StatsTicket;

  timeseries: StatsTimeseriesItem[];

  tickets_timeseries: StatsTicketTimeseriesItem[];

  actions_timeseries: StatsActionTimeseriesItem[];
}

export interface Item {
  id: number;
  name: string;
}

export interface ContextMenuPosition {
  x: number;
  y: number;
}

export interface ContextMenuState extends ContextMenuPosition {
  itemId: number;
  isFavorite: boolean;
  isOpen: boolean;
}

export interface StaffFavoriteStatus {
  user_id: number;
  is_favorite: boolean;
  my_favorite: boolean;
}
