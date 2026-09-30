import { api } from "@/api/client";
import type {
  AdminAttemptDetail,
  AdminAttemptSummary,
  AdminTestDetail,
  AdminTestSummary,
  ConsentDocumentDetail,
  ConsentDocumentSave,
  ConsentDocumentSummary,
  FormTestSchema,
  TestAttemptStatus,
  TestCreate,
  TestDraft,
  TestPreviewResult,
  TestSchemaExport,
} from "@/entities/form-test/model/types";

export const formTestApi = {
  list: () => api.get<AdminTestSummary[]>("/form-tests/admin"),
  detail: (testId: number) =>
    api.get<AdminTestDetail>(`/form-tests/admin/${testId}`),
  updateTest: (
    testId: number,
    payload: Partial<Pick<AdminTestSummary, "is_active" | "is_archived">>,
  ) => api.patch<AdminTestSummary>(`/form-tests/admin/${testId}`, payload),
  listAttempts: (testId: number, status?: TestAttemptStatus) =>
    api.get<AdminAttemptSummary[]>(
      `/form-tests/admin/${testId}/attempts${status ? `?status=${status}` : ""}`,
    ),
  attemptDetail: (testId: number, attemptId: number) =>
    api.get<AdminAttemptDetail>(
      `/form-tests/admin/${testId}/attempts/${attemptId}`,
    ),
  exportAttemptsBlob: (testId: number, valueMode: "text" | "score" = "text") =>
    api.getBlob(`/form-tests/admin/${testId}/attempts/export.xlsx?value_mode=${valueMode}`),

  create: (payload: TestCreate) =>
    api.post<AdminTestSummary>("/form-tests/admin", payload),
  reorder: (testIds: number[]) =>
    api.post<AdminTestSummary[]>("/form-tests/admin/reorder", {
      test_ids: testIds,
    }),
  getDraft: (testId: number) =>
    api.get<TestDraft>(`/form-tests/admin/${testId}/draft`),
  saveDraft: (testId: number, draft: TestDraft) =>
    api.put<TestDraft>(`/form-tests/admin/${testId}/draft`, {
      expected_revision: draft.revision,
      name: draft.name,
      intro_text: draft.intro_text,
      test_schema: draft.test_schema,
      consent_enabled: draft.consent_enabled,
      consent_document_id: draft.consent_document_id,
      consent_checkbox_text: draft.consent_checkbox_text,
      allow_retake: draft.allow_retake,
      show_attempt_history: draft.show_attempt_history,
      show_scores: draft.show_scores,
    }),
  publish: (testId: number, expectedRevision: number) =>
    api.post<AdminTestDetail>(`/form-tests/admin/${testId}/publish`, {
      expected_revision: expectedRevision,
    }),
  preview: (
    testId: number,
    payload: {
      filters: FormTestSchema["filters"];
      result_template: string;
      sample_values: Record<string, number>;
    },
  ) =>
    api.post<TestPreviewResult>(`/form-tests/admin/${testId}/preview`, payload),
  exportDraftBlob: (testId: number) =>
    api.getBlob(`/form-tests/admin/${testId}/draft/export.xlsx`),
  exportVersionBlob: (testId: number, versionId: number) =>
    api.getBlob(`/form-tests/admin/${testId}/versions/${versionId}/export.xlsx`),
  importDraftXlsx: (testId: number, file: File) =>
    api.postFile<TestSchemaExport>(
      `/form-tests/admin/${testId}/draft/import.xlsx`,
      file,
    ),

  listConsentDocuments: () =>
    api.get<ConsentDocumentSummary[]>("/form-tests/admin/consent-documents"),
  getConsentDocument: (documentId: number) =>
    api.get<ConsentDocumentDetail>(`/form-tests/admin/consent-documents/${documentId}`),
  createConsentDocument: (payload: ConsentDocumentSave) =>
    api.post<ConsentDocumentDetail>("/form-tests/admin/consent-documents", payload),
  updateConsentDocument: (documentId: number, payload: ConsentDocumentSave) =>
    api.put<ConsentDocumentDetail>(`/form-tests/admin/consent-documents/${documentId}`, payload),
  deleteConsentDocument: (documentId: number) =>
    api.del<void>(`/form-tests/admin/consent-documents/${documentId}`),
};
