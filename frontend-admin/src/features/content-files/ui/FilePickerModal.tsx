import type { ContentAttachmentOption } from '@/entities/content/model/types'
import { FilesBrowser } from '@/features/content-files/ui/FilesBrowser'

/**
 * Modal wrapper around `FilesBrowser` -- the picker half of Task 025's "one component, two
 * render modes" (the other half is the full `/files` page). Replaces the old bare `<select>`
 * pickers in ContentDraftEditor / FileListBlockEditor.
 */
export function FilePickerModal({
  title,
  imageOnly = false,
  onPick,
  onUploaded,
  onClose,
  uploadPurpose,
}: {
  title: string
  imageOnly?: boolean
  onPick: (attachment: ContentAttachmentOption) => void
  onUploaded?: (attachment: ContentAttachmentOption) => void
  onClose: () => void
  /** Forwarded to `FilesBrowser` -- see its `uploadPurpose` doc (Task 065). */
  uploadPurpose?: string
}) {
  return (
    <div
      className='submission-preview'
      role='dialog'
      aria-modal='true'
      aria-label={title}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}>
      <section className='submission-preview__dialog content-files-modal'>
        <header className='submission-preview__header'>
          <div>
            <strong>{title}</strong>
          </div>
          <button className='btn btn-ghost btn-icon' type='button' aria-label='Закрыть' onClick={onClose}>
            ×
          </button>
        </header>
        <div className='content-files-modal__body'>
          <FilesBrowser
            imageOnly={imageOnly}
            onUploaded={onUploaded}
            uploadPurpose={uploadPurpose}
            onPick={(attachment) => {
              onPick(attachment)
              onClose()
            }}
          />
        </div>
      </section>
    </div>
  )
}
