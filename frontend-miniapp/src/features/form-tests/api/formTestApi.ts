import { api } from "@/api/client";
import type {
  PublishedTestDetail,
  PublishedTestSummary,
  TestAttempt,
} from "@/entities/form-test/model/types";

export const formTestApi = {
  list: () => api.get<PublishedTestSummary[]>("/form-tests"),
  get: (testId: number) => api.get<PublishedTestDetail>(`/form-tests/${testId}`),
  getConsentDocument: (testId: number) =>
    api
      .get<{ title: string; body_html: string }>(`/form-tests/${testId}/consent-document`)
      .then((r) => r.body_html),
  startAttempt: (testId: number) =>
    api.post<TestAttempt>(`/form-tests/${testId}/attempts`),
  retake: (testId: number) =>
    api.post<TestAttempt>(`/form-tests/${testId}/attempts/retake`),
  autosave: (attemptId: number, answers: Record<string, unknown>) =>
    api.patch<TestAttempt>(`/form-tests/attempts/${attemptId}`, { answers }),
  complete: (attemptId: number, consentAccepted: boolean) =>
    api.post<TestAttempt>(`/form-tests/attempts/${attemptId}/complete`, {
      consent_accepted: consentAccepted,
    }),
  getAttempt: (attemptId: number) =>
    api.get<TestAttempt>(`/form-tests/attempts/${attemptId}`),
  listMyAttempts: () => api.get<TestAttempt[]>("/form-tests/attempts"),
};
