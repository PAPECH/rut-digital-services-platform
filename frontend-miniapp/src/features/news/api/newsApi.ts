import { api } from "@/api/client";
import type { NewsItem } from "@/entities/news/model/types";

export const newsApi = {
  list: () => api.get<NewsItem[]>("/news"),
  recordOpen: () => api.post<void>("/news/events/open"),
  recordItemOpen: (id: number) => api.post<void>(`/news/${id}/events/open`),
};
