import { useCallback, useEffect, useState } from 'react'

import { uploadFile } from '@/api/files'
import type { ApiError } from '@/api/client'
import type { ContentAttachmentOption } from '@/entities/content/model/types'
import { contentApi } from '@/features/content-management/api/contentApi'

export const FILES_PAGE_SIZE = 30

export type MimeFilter = 'all' | 'image' | 'other'

export interface AttachmentInUseError {
  ok: false
  code: 'in_use'
  message: string
  categoryIds: number[]
}

export interface AttachmentDeleteFailure {
  ok: false
  code: 'error'
  message: string
}

export type AttachmentDeleteResult = { ok: true } | AttachmentInUseError | AttachmentDeleteFailure

/**
 * Backs both the full-page "Файлы бота" list and the picker modal opened from the content
 * editors (Task 025) -- one fetch/pagination/search implementation so the two surfaces can't
 * drift apart.
 */
export function useContentFiles() {
  const [items, setItems] = useState<ContentAttachmentOption[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [search, setSearchState] = useState('')
  const [mimeFilter, setMimeFilterState] = useState<MimeFilter>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const reload = useCallback(() => {
    setLoading(true)
    setError(null)
    contentApi
      .listAttachments({
        limit: FILES_PAGE_SIZE,
        offset,
        mime: mimeFilter === 'all' ? undefined : mimeFilter,
        q: search.trim() || undefined,
      })
      .then((page) => {
        setItems(page.items)
        setTotal(page.total)
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : 'Не удалось загрузить файлы')
      })
      .finally(() => setLoading(false))
  }, [offset, mimeFilter, search])

  useEffect(() => {
    const id = setTimeout(reload, search ? 250 : 0)
    return () => clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset, mimeFilter, search])

  const setSearch = useCallback((value: string) => {
    setOffset(0)
    setSearchState(value)
  }, [])

  const setMimeFilter = useCallback((value: MimeFilter) => {
    setOffset(0)
    setMimeFilterState(value)
  }, [])

  const upload = useCallback(
    async (file: File, purpose?: string): Promise<ContentAttachmentOption | null> => {
      setUploading(true)
      setError(null)
      try {
        const uploaded = await uploadFile(file, purpose)
        setOffset(0)
        reload()
        return {
          ...uploaded,
          created_at: new Date().toISOString(),
          referenced_by_draft: [],
          referenced_by_published: [],
        }
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Не удалось загрузить файл')
        return null
      } finally {
        setUploading(false)
      }
    },
    [reload],
  )

  const remove = useCallback(
    async (attachment: ContentAttachmentOption): Promise<AttachmentDeleteResult> => {
      setDeletingId(attachment.id)
      try {
        await contentApi.deleteAttachment(attachment.id)
        reload()
        return { ok: true }
      } catch (reason) {
        const apiError = reason as ApiError
        if (apiError.code === 'content_attachment_in_use') {
          const detail = apiError.detail as { detail?: { category_ids?: number[] } } | undefined
          return {
            ok: false,
            code: 'in_use',
            message: apiError.message,
            categoryIds: detail?.detail?.category_ids ?? [],
          }
        }
        return { ok: false, code: 'error', message: apiError.message || 'Не удалось удалить файл' }
      } finally {
        setDeletingId(null)
      }
    },
    [reload],
  )

  return {
    items,
    total,
    offset,
    limit: FILES_PAGE_SIZE,
    search,
    mimeFilter,
    loading,
    error,
    uploading,
    deletingId,
    setOffset,
    setSearch,
    setMimeFilter,
    upload,
    remove,
    reload,
  }
}
