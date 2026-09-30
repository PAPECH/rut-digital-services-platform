export type FormTestElementType =
  | "questionnaire_title"
  | "section_title"
  | "instruction"
  | "text"
  | "single_choice"
  | "multiple_choice"
  | "scale";

export interface FormTestOption {
  value: string;
  label: string;
  score: number;
}

export interface FormTestElement {
  key: string;
  type: FormTestElementType;
  label: string;
  required?: boolean;
  scoring_key?: string | null;
  options?: FormTestOption[];
}

export interface ResultScaleTerm {
  question_key: string | null;
  result_scale_key: string | null;
  weight: number;
}

export interface ResultScale {
  key: string;
  label: string;
  terms: ResultScaleTerm[];
  constant: number;
  aggregation: "sum" | "mean";
}

export interface FilterRule {
  min: number | null;
  max: number | null;
  label: string;
  is_flagged: boolean;
  recommendation_text: string | null;
}

export interface ResultFilter {
  result_scale_key: string;
  rules: FilterRule[];
}

export interface FormTestSchema {
  elements: FormTestElement[];
  result_scales: ResultScale[];
  filters: ResultFilter[];
  result_template: string;
}

export type TestAttemptStatus = "in_progress" | "completed";

export interface AdminTestSummary {
  id: number;
  slug: string;
  name: string;
  order: number;
  is_active: boolean;
  is_archived: boolean;
  published_version_id: number | null;
  last_published_revision: number;
}

export interface AdminTestDetail extends AdminTestSummary {
  intro_text: string | null;
  test_schema: FormTestSchema;
  consent_enabled: boolean;
  consent_document_title: string | null;
  consent_checkbox_text: string | null;
  allow_retake: boolean;
  show_attempt_history: boolean;
  show_scores: boolean;
}

export interface TestCreate {
  slug: string;
  name: string;
  order: number;
}

export interface TestDraft {
  test_id: number;
  name: string;
  intro_text: string | null;
  test_schema: FormTestSchema;
  revision: number;
  updated_at: string | null;
  consent_enabled: boolean;
  consent_document_id: number | null;
  consent_document_title: string | null;
  consent_document_missing: boolean;
  consent_checkbox_text: string | null;
  allow_retake: boolean;
  show_attempt_history: boolean;
  show_scores: boolean;
}

export interface ConsentDocumentSummary {
  id: number;
  title: string;
  updated_at: string | null;
}

export interface ConsentDocumentDetail extends ConsentDocumentSummary {
  body_html: string;
  created_at: string | null;
}

export interface ConsentDocumentSave {
  title: string;
  body_html: string;
}

export interface TestSchemaExport {
  name: string;
  intro_text: string | null;
  test_schema: FormTestSchema;
}

export interface TestPreviewResult {
  rendered_text: string;
  chunks: string[];
}

export interface ComputedResultEntry {
  value: number;
  aggregation: "sum" | "mean";
  filter: FilterRule | null;
}

export interface AttemptSubmitter {
  id: number;
  first_name: string | null;
  last_name: string | null;
  patronymic: string | null;
  username: string | null;
  photo_url: string | null;
}

export interface AdminAttemptSummary {
  id: number;
  user_id: number;
  submitter: AttemptSubmitter | null;
  answers: Record<string, unknown>;
  computed_results: Record<string, ComputedResultEntry> | null;
  status: TestAttemptStatus;
  started_at: string;
  completed_at: string | null;
  consent_accepted: boolean;
  consent_accepted_at: string | null;
}

export interface AdminAttemptDetail extends AdminAttemptSummary {
  rendered_result_text: string | null;
}
