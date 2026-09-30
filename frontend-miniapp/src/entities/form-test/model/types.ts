export type FormTestElementType =
  | "questionnaire_title"
  | "section_title"
  | "instruction"
  | "text"
  | "single_choice"
  | "multiple_choice"
  | "scale";

/** Student-facing option -- the backend strips `score` before it ever reaches this app. */
export interface FormTestOption {
  value: string;
  label: string;
}

export interface FormTestElement {
  key: string;
  type: FormTestElementType;
  label: string;
  required?: boolean;
  scoring_key?: string | null;
  options?: FormTestOption[];
}

export interface PublishedTestSummary {
  id: number;
  slug: string;
  name: string;
  version_id: number;
  version: number;
}

export interface PublishedTestDetail extends PublishedTestSummary {
  intro_text: string | null;
  elements: FormTestElement[];
  consent_enabled: boolean;
  consent_checkbox_text: string | null;
  consent_document_title: string | null;
  allow_retake: boolean;
  /** Result-scale key -> human label; present only when the version has scores turned on. */
  result_scale_labels: Record<string, string> | null;
}

export type TestAttemptStatus = "in_progress" | "completed";

/** A matched interpretation-filter rule for one result scale (see `ComputedResultEntry`). */
export interface ComputedResultFilter {
  label: string;
  is_flagged: boolean;
  recommendation_text: string | null;
}

export interface ComputedResultEntry {
  value: number;
  aggregation: "sum" | "mean";
  filter: ComputedResultFilter | null;
}

export interface TestAttempt {
  id: number;
  test_definition_id: number;
  test_version_id: number;
  status: TestAttemptStatus;
  answers: Record<string, unknown>;
  /** `null` both before completion and when the test's `show_scores` setting is off. */
  computed_results: Record<string, ComputedResultEntry> | null;
  rendered_result_text: string | null;
  started_at: string;
  completed_at: string | null;
  consent_accepted: boolean;
  consent_accepted_at: string | null;
}
