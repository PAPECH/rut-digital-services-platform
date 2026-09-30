import { useEffect, useState } from 'react'

import { formatBytes, isImageMime } from '@/api/files'
import { Icon } from '@/components/Icon'
import type { ContentAttachmentOption } from '@/entities/content/model/types'
import { formatDateTime } from '@/lib/status'
import type { MimeFilter } from '@/features/content-files/model/useContentFiles'
import { useContentFiles } from '@/features/content-files/model/useContentFiles'
import { ContentAttachmentPreview } from '@/features/content-files/ui/ContentAttachmentPreview'

/**
 * The single "browse this bot's files" implementation (Task 025) -- rendered full-page at
 * /files and inside the picker modal opened from ContentDraftEditor / FileListBlockEditor. Both
 * surfaces share this component and its `useContentFiles` fetch so they can't drift apart.
 */
export function FilesBrowser({
  onPick,
  imageOnly = false,
  onUploaded,
  uploadPurpose,
}: {
  /** Present in picker mode: renders a "Выбрать" action per row instead of just browsing. */
  onPick?: (attachment: ContentAttachmentOption) => void
  /** Force the image filter and hide the "Остальные" tab -- used when picking a card image. */
  imageOnly?: boolean
  /** Notified after a successful upload so callers can keep their own attachment cache warm. */
  onUploaded?: (attachment: ContentAttachmentOption) => void
  /** Forwarded to POST /api/files as `purpose` for a *new* upload (Task 065) -- e.g.
   * `category_icon` resizes/converts to a 128x128 WEBP server-side. Files picked from the
   * existing library, rather than freshly uploaded, are never reprocessed. */
  uploadPurpose?: string
}) {
  const files = useContentFiles()
  const [previewItem, setPreviewItem] = useState<ContentAttachmentOption | null>(null)
  const [pendingUpload, setPendingUpload] = useState(false)

  useEffect(() => {
    if (imageOnly) files.setMimeFilter('image')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageOnly])

  const effectiveMimeFilter: MimeFilter = imageOnly ? 'image' : files.mimeFilter

  const handleUpload = async (file: File) => {
    if (imageOnly && !file.type.startsWith('image/')) return
    setPendingUpload(true)
    try {
      const uploaded = await files.upload(file, uploadPurpose)
      if (uploaded) {
        onUploaded?.(uploaded)
        onPick?.(uploaded)
      }
    } finally {
      setPendingUpload(false)
    }
  }

  const handleDelete = async (attachment: ContentAttachmentOption) => {
    const usedInDrafts = attachment.referenced_by_draft.length
    if (!window.confirm(`Удалить файл «${attachment.name}»?`)) return
    const result = await files.remove(attachment)
    if (result.ok) {
      if (usedInDrafts > 0) {
        window.alert(
          `Файл удалён. Он был использован в ${usedInDrafts} черновике(ах) — там останется недоступная ссылка, отредактируйте эти черновики.`,
        )
      }
      return
    }
    if (result.code === 'in_use') {
      window.alert(
        `${result.message}. Категории: ${result.categoryIds.join(', ') || '—'}. Сначала уберите файл из опубликованной версии.`,
      )
      return
    }
    window.alert(result.message)
  }

  const from = files.total === 0 ? 0 : files.offset + 1
  const to = Math.min(files.offset + files.limit, files.total)

  return (
    <div className='content-files-browser'>
      <div className='content-files-toolbar'>
        <input
          className='input'
          placeholder='Поиск по названию файла…'
          value={files.search}
          onChange={(event) => files.setSearch(event.target.value)}
        />
        {!imageOnly ? (
          <div className='content-files-tabs' role='tablist' aria-label='Тип файла'>
            {(
              [
                ['all', 'Все'],
                ['image', 'Картинки'],
                ['other', 'Остальные'],
              ] as Array<[MimeFilter, string]>
            ).map(([value, label]) => (
              <button
                type='button'
                key={value}
                role='tab'
                aria-selected={files.mimeFilter === value}
                className={files.mimeFilter === value ? 'active' : ''}
                onClick={() => files.setMimeFilter(value)}>
                {label}
              </button>
            ))}
          </div>
        ) : null}
        <label className='btn btn-secondary btn-sm content-file-upload'>
          {pendingUpload || files.uploading ? 'Загрузка…' : 'Загрузить файл'}
          <input
            type='file'
            accept={imageOnly ? 'image/*' : undefined}
            disabled={pendingUpload || files.uploading}
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (file) void handleUpload(file)
              event.target.value = ''
            }}
          />
        </label>
      </div>

      {files.error ? <p className='form-error'>{files.error}</p> : null}

      <div className='content-files-table-wrap'>
        <table className='tbl content-files-table'>
          <thead>
            <tr>
              <th aria-hidden='true' />
              <th>Файл</th>
              <th>Размер</th>
              <th>Загружен</th>
              <th>Используется</th>
              <th aria-hidden='true' />
            </tr>
          </thead>
          <tbody>
            {files.items
              .filter((item) => (imageOnly ? isImageMime(item.mime) : true))
              .map((item) => {
                const image = isImageMime(item.mime)
                const publishedCount = item.referenced_by_published.length
                const draftCount = item.referenced_by_draft.length
                return (
                  <tr key={item.id}>
                    <td>
                      {image ? (
                        <button
                          type='button'
                          className='content-files-thumb'
                          aria-label={`Предпросмотр ${item.name}`}
                          onClick={() => setPreviewItem(item)}>
                          <img src={item.url} alt='' />
                        </button>
                      ) : (
                        <span className='content-files-thumb content-files-thumb--icon'>
                          <Icon.Paperclip />
                        </span>
                      )}
                    </td>
                    <td>
                      <strong className='content-files-name'>{item.name}</strong>
                      <span className='muted content-files-mime'>{item.mime}</span>
                    </td>
                    <td>{formatBytes(item.size_bytes)}</td>
                    <td>{formatDateTime(item.created_at)}</td>
                    <td>
                      {publishedCount === 0 && draftCount === 0 ? (
                        <span className='muted'>не используется</span>
                      ) : (
                        <span className='content-files-usage'>
                          {publishedCount > 0 ? (
                            <span className='tag done'>опубликовано × {publishedCount}</span>
                          ) : null}
                          {draftCount > 0 ? <span className='tag neutral'>черновик × {draftCount}</span> : null}
                        </span>
                      )}
                    </td>
                    <td>
                      <div className='content-files-actions'>
                        {onPick ? (
                          <button type='button' className='btn btn-primary btn-sm' onClick={() => onPick(item)}>
                            Выбрать
                          </button>
                        ) : null}
                        <button
                          type='button'
                          className='btn btn-secondary btn-sm'
                          disabled={files.deletingId === item.id}
                          onClick={() => void handleDelete(item)}>
                          {files.deletingId === item.id ? 'Удаление…' : 'Удалить'}
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            {!files.loading && files.items.length === 0 ? (
              <tr>
                <td colSpan={6} className='muted'>
                  {files.search || effectiveMimeFilter !== 'all' ? 'Ничего не найдено' : 'Файлов пока нет'}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {files.loading ? <p className='muted'>Загрузка…</p> : null}

      {files.total > files.limit ? (
        <div className='content-files-pagination'>
          <span className='muted'>
            {from}–{to} из {files.total}
          </span>
          <div className='content-files-pagination-buttons'>
            <button
              type='button'
              className='btn btn-secondary btn-sm'
              disabled={files.offset === 0}
              onClick={() => files.setOffset(Math.max(0, files.offset - files.limit))}>
              Назад
            </button>
            <button
              type='button'
              className='btn btn-secondary btn-sm'
              disabled={files.offset + files.limit >= files.total}
              onClick={() => files.setOffset(files.offset + files.limit)}>
              Вперёд
            </button>
          </div>
        </div>
      ) : null}

      {previewItem ? (
        <ContentAttachmentPreview name={previewItem.name} url={previewItem.url} onClose={() => setPreviewItem(null)} />
      ) : null}
    </div>
  )
}
