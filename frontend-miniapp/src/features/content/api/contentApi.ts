import { api } from "@/api/client";
import type {
  PublishedCategorySummary,
  PublishedContent,
} from "@/entities/content/model/types";

export const contentApi = {
  catalog: () => api.get<PublishedContent[]>("/content/catalog"),
  list: () => api.get<PublishedCategorySummary[]>("/content/categories"),
  get: (slug: string) =>
    api.get<PublishedContent>(
      `/content/categories/${encodeURIComponent(slug)}`,
    ),
  home: () => api.get<PublishedContent>("/content/categories/home"),
};
