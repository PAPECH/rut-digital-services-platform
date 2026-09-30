import { api } from '@/api/client'
import type { NewsBodyBlock } from '@/entities/content/model/types'

export interface NewsItem {
  id: number
  bot_instance_id: number
  title: string
  title_en: string | null
  body_blocks: NewsBodyBlock[]
  category: string | null
  cover_attachment_id: number | null
  cover_url: string | null
  is_active: boolean
  published_at: string
  created_at: string | null
  updated_at: string | null
}

export interface NewsItemInput {
  title: string
  title_en: string | null
  body_blocks: NewsBodyBlock[]
  category: string | null
  cover_attachment_id: number | null
  is_active: boolean
  published_at: string | null
}

export const newsApi = {
  list: () => api.get<NewsItem[]>('/news'),
  create: (input: NewsItemInput) => api.post<NewsItem>('/news', input),
  update: (id: number, input: Partial<NewsItemInput>) => api.patch<NewsItem>(`/news/${id}`, input),
  remove: (id: number) => api.del(`/news/${id}`),
}
