import { api } from "@/api/client";
import type { FaqItem } from "@/entities/faq/model/types";

export const faqApi = {
  list: () => api.get<FaqItem[]>("/faq"),
  recordOpen: () => api.post<void>("/faq/events/open"),
};
