import { useEffect } from 'react'

/**
 * Lightbox for an image `file_list` attachment (Task 025). Content attachment URLs are public,
 * non-expiring signed `/api/files/...` links served same-origin with no auth needed, so unlike
 * `SubmissionAttachmentPreview` this points `<img>` straight at the URL instead of fetching an
 * authenticated blob first.
 */
export function ContentAttachmentPreview({
  name,
  url,
  onClose,
}: {
  name: string
  url: string
  onClose: () => void
}) {
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [onClose])

  return (
    <div
      className='history-file-preview'
      role='dialog'
      aria-modal='true'
      aria-label={`Предпросмотр: ${name}`}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}>
      <section className='history-file-preview__dialog'>
        <header>
          <div>
            <strong>{name}</strong>
          </div>
          <button type='button' aria-label='Закрыть' onClick={onClose}>
            ×
          </button>
        </header>
        <div className='history-file-preview__body'>
          <img src={url} alt={name} />
        </div>
      </section>
    </div>
  )
}
