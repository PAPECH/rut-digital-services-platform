import { api } from "@/api/client";
import type {
  PublishedForm,
  PublishedFormSummary,
  UploadedAttachment,
} from "@/entities/form/model/types";
export const formApi = {
  list: () => api.get<PublishedFormSummary[]>("/forms"),
  get: (formId: number) => api.get<PublishedForm>(`/forms/${formId}`),
  upload: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return api.upload<UploadedAttachment>("/files", body);
  },
};
