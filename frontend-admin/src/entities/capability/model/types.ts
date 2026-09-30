import type { CapabilityInstallation } from "@/api/types";

export interface RequestStatusConfig {
  provider: "google_sheets";
  credential_ref: "mock" | "legacy_google_sheets";
  spreadsheet_id: string;
  sheet_range: string;
  request_number_column: number;
  status_column: number;
  normalization: "trim" | "compact";
  polling_interval_seconds: number;
  notifications_enabled: boolean;
  title: string;
  subtitle: string;
  lookup_label: string;
  not_found_text: string;
}

export interface AdmissionRatingConfig {
  provider: "rut_admission";
  admission_year: number;
  polling_interval_seconds: number;
  notifications_enabled: boolean;
  title: string;
  subtitle: string;
  lookup_label: string;
  not_found_text: string;
}

export const defaultAdmissionRatingConfig: AdmissionRatingConfig = {
  provider: "rut_admission",
  admission_year: new Date().getFullYear(),
  polling_interval_seconds: 900,
  notifications_enabled: true,
  title: "Место в рейтинге",
  subtitle: "Введите уникальный код поступающего.",
  lookup_label: "Уникальный код поступающего",
  not_found_text: "Записи в рейтинге не найдены.",
};

export interface RutScheduleConfig {
  provider: "miit_timetable";
  title: string;
  subtitle: string;
  group_cache_ttl_seconds: number;
  hierarchy_sync_interval_seconds: number;
  // Platform-admin-only (Task 045) -- not rendered by RutScheduleCapabilityEditor, but every
  // save from that editor must still carry the current value through unchanged (see
  // configFrom's merge-with-defaults pattern), or a bot-admin save would silently reset it.
  night_auto_sync_enabled: boolean;
}

export const defaultRutScheduleConfig: RutScheduleConfig = {
  provider: "miit_timetable",
  title: "Расписание",
  subtitle: "Выберите институт, курс и группу, чтобы посмотреть расписание занятий.",
  group_cache_ttl_seconds: 900,
  hierarchy_sync_interval_seconds: 21_600,
  night_auto_sync_enabled: true,
};

// --- Platform-admin manual sync controls (Task 045) ---

export interface RutScheduleInstitute {
  external_id: string;
  name: string;
}

export interface RutScheduleGroup {
  external_id: string;
  name: string;
  institute_external_id: string;
  course_number: number;
}

export interface RutScheduleManualSyncRequest {
  id: number;
  requested_at: string;
  requested_by_admin_id: number | null;
  requested_by_admin_name: string | null;
  provider: string;
  scope: "group" | "institute" | "all";
  group_external_id: string | null;
  group_name: string | null;
  institute_external_id: string | null;
  institute_name: string | null;
  status: "queued" | "running" | "succeeded" | "failed" | "partial";
  started_at: string | null;
  finished_at: string | null;
  groups_synced: number | null;
  groups_failed: number | null;
  error_code: string | null;
}

export interface RutScheduleGroupWithLastSync {
  group: RutScheduleGroup;
  last_synced_at: string | null;
}

export interface RutScheduleRefreshGroupsResult {
  institutes_count: number;
  groups_count: number;
}

export interface CapabilityEditorProps {
  installation: CapabilityInstallation;
  busy: string | null;
  onSave: (config: Record<string, unknown>) => Promise<void>;
  onTest: () => Promise<void>;
}

export const defaultRequestStatusConfig: RequestStatusConfig = {
  provider: "google_sheets",
  credential_ref: "legacy_google_sheets",
  spreadsheet_id: "legacy",
  sheet_range: "B:C",
  request_number_column: 0,
  status_column: 1,
  normalization: "trim",
  polling_interval_seconds: 300,
  notifications_enabled: true,
  title: "Проверить статус заявления",
  subtitle: "Введите номер заявления, чтобы узнать актуальный статус.",
  lookup_label: "Номер заявления",
  not_found_text: "Заявление с таким номером не найдено.",
};
