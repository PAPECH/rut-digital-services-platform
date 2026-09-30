import { api } from "@/api/client";
import type {
  AdminForm,
  FormCreate,
  FormDraft,
  PublishedForm,
  SharedFormDraft,
} from "@/entities/form/model/types";

export const formApi = {
  list: () => api.get<AdminForm[]>("/forms/admin"),
  create: (payload: FormCreate) => api.post<AdminForm>("/forms/admin", payload),
  patch: (
    formId: number,
    payload: Partial<
      Pick<AdminForm, "order" | "is_active" | "show_in_catalog" | "is_archived">
    >,
  ) => api.patch<AdminForm>(`/forms/admin/${formId}`, payload),
  saveDraft: (draft: FormDraft) =>
    api.put<FormDraft>(`/forms/admin/${draft.form_id}/draft`, {
      expected_revision: draft.revision,
      name: draft.name,
      description: draft.description,
      reply_on_accept: draft.reply_on_accept,
      fields: draft.fields,
      is_shared: draft.is_shared,
    }),
  publish: (formId: number, expectedRevision: number) =>
    api.post<PublishedForm>(`/forms/admin/${formId}/publish`, {
      expected_revision: expectedRevision,
    }),
  reorder: (formIds: number[]) =>
    api.post<AdminForm[]>("/forms/admin/reorder", { form_ids: formIds }),
  listSharedDrafts: () =>
    api.get<SharedFormDraft[]>("/forms/admin/shared-drafts"),
  importSharedDraft: (sourceFormId: number, slug: string, order: number) =>
    api.post<AdminForm>(`/forms/admin/shared-drafts/${sourceFormId}/import`, {
      slug,
      order,
    }),
};
