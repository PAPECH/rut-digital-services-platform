import type { PublicCapability } from "@/api/types";

export interface CapabilityViewProps {
  capability: PublicCapability;
  viewKey: string;
}

export interface RequestStatusPublicConfig {
  title: string;
  subtitle: string;
  lookup_label: string;
  not_found_text: string;
  notifications_enabled: boolean;
}

export interface RequestStatusLookup {
  request_number: string;
  status: string | null;
  checked_at: string | null;
  is_subscribed: boolean;
}

export interface RequestStatusSubscription {
  request_number: string | null;
  is_active: boolean;
  last_status: string | null;
  checked_at: string | null;
}

export interface AdmissionRatingPublicConfig {
  admission_year: number;
  title: string;
  subtitle: string;
  lookup_label: string;
  not_found_text: string;
  notifications_enabled: boolean;
}

export interface AdmissionRatingEntry {
  plan_id: number;
  specialty: string;
  qualification: string;
  points: number;
  preference: string;
  competition: string;
  group_name: string;
  position: number;
  total: number;
  checked_at: string;
}

export interface AdmissionRatingLookup {
  applicant_code: string;
  entries: AdmissionRatingEntry[];
  is_subscribed: boolean;
}

export interface AdmissionRatingSubscription {
  applicant_code: string | null;
  is_active: boolean;
}

export interface RutSchedulePublicConfig {
  title: string;
  subtitle: string;
}

export interface RutScheduleInstitute {
  external_id: string;
  name: string;
}

export interface RutScheduleCourse {
  course_number: number;
}

export interface RutScheduleGroup {
  external_id: string;
  name: string;
  institute_external_id: string;
  course_number: number;
}

// The whole institutes->courses->groups catalog, fetched once instead of one request per
// drill-down step (Task 046) -- Redis-cached server-side, invalidated whenever the nightly crawl
// or an admin-triggered "refresh groups" replaces the catalog.
export interface RutScheduleNavigationCourse {
  course_number: number;
  groups: RutScheduleGroup[];
}

export interface RutScheduleNavigationInstitute {
  external_id: string;
  name: string;
  courses: RutScheduleNavigationCourse[];
}

export interface RutScheduleNavigationTree {
  institutes: RutScheduleNavigationInstitute[];
}

export interface RutScheduleLesson {
  weekday: number;
  week_parity: number;
  period_label: string;
  start_time: string;
  end_time: string;
  lesson_kind: string;
  discipline: string;
  room: string | null;
  teachers: string | null;
  combined_groups: string | null;
  // Reserved for the future Oracle provider; always null while the miit.ru scraper is the active
  // provider. Not used by any display logic yet — see docs/tasks/043-rut-schedule-capability.md.
  periodicity_code: number | null;
  // ISO date string ("YYYY-MM-DD"), set only for a "Разовое" (one-off, explicitly dated)
  // session. week_parity is meaningless whenever this is set — match on this date directly
  // instead of weekday/week_parity when it's present.
  lesson_date: string | null;
}

export interface RutGroupSchedule {
  group: RutScheduleGroup;
  lessons: RutScheduleLesson[];
  synced_at: string;
  // ISO date strings ("YYYY-MM-DD"), or null if the source page didn't expose them -- the anchor
  // needed to map a calendar date to week_parity 1/2.
  semester_start: string | null;
  semester_end: string | null;
}
