import { api } from '@/api/client'
import type {
  AdminContentCategory,
  ContentAttachmentPage,
  ContentFormOption,
  ContentTestOption,
  ContentCategoryCreate,
  ContentDraft,
  PublishedContent,
  SharedContentDraft,
  SharedContentDependencyReport,
  SharedContentImportResult,
  ContentFormDependencyResolution,
} from '@/entities/content/model/types'

export interface ListAttachmentsParams {
  limit?: number
  offset?: number
  mime?: 'image' | 'other'
  q?: string
}

function attachmentsQuery(params: ListAttachmentsParams): string {
  const search = new URLSearchParams()
  search.set('limit', String(params.limit ?? 50))
  search.set('offset', String(params.offset ?? 0))
  if (params.mime) search.set('mime', params.mime)
  if (params.q) search.set('q', params.q)
  return search.toString()
}

export const contentApi = {
  list: () => api.get<AdminContentCategory[]>('/content/admin/categories'),
  listAttachments: (params: ListAttachmentsParams = {}) =>
    api.get<ContentAttachmentPage>(`/content/admin/attachments?${attachmentsQuery(params)}`),
  deleteAttachment: (attachmentId: number) =>
    api.del<void>(`/content/admin/attachments/${attachmentId}`),
  listForms: () => api.get<ContentFormOption[]>('/content/admin/forms'),
  listTests: () => api.get<ContentTestOption[]>('/content/admin/tests'),
  create: (payload: ContentCategoryCreate) =>
    api.post<AdminContentCategory>('/content/admin/categories', payload),
  patch: (
    categoryId: number,
    payload: Partial<
      Pick<
        AdminContentCategory,
        'parent_id' | 'icon' | 'order' | 'is_active' | 'title' | 'subtitle' | 'image_url'
      >
    >,
  ) => api.patch<AdminContentCategory>(`/content/admin/categories/${categoryId}`, payload),
  saveDraft: (draft: ContentDraft) =>
    api.put<ContentDraft>(`/content/admin/categories/${draft.category_id}/draft`, {
      expected_revision: draft.revision,
      title: draft.title,
      subtitle: draft.subtitle,
      language: draft.language,
      blocks: draft.blocks,
      is_shared: draft.is_shared,
      is_filled: draft.is_filled,
      image_url: draft.image_url,
      header_visible: draft.header_visible,
    }),
  publish: (categoryId: number, expectedRevision: number) =>
    api.post<PublishedContent>(`/content/admin/categories/${categoryId}/publish`, {
      expected_revision: expectedRevision,
    }),
  reorder: (categoryIds: number[]) =>
    api.post<AdminContentCategory[]>('/content/admin/categories/reorder', {
      category_ids: categoryIds,
    }),
  listSharedDrafts: () => api.get<SharedContentDraft[]>('/content/admin/shared-drafts'),
  getSharedDraftDependencies: (sourceCategoryId: number) =>
    api.get<SharedContentDependencyReport>(`/content/admin/shared-drafts/${sourceCategoryId}/dependencies`),
  importSharedDraft: (
    sourceCategoryId: number,
    slug: string,
    parentId: number | null,
    order: number,
    resolutions: ContentFormDependencyResolution[],
  ) =>
    api.post<SharedContentImportResult>(`/content/admin/shared-drafts/${sourceCategoryId}/import`, {
      slug,
      parent_id: parentId,
      order,
      resolutions,
    }),
}
