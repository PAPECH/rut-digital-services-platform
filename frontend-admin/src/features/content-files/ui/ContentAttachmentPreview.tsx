import { useEffect } from 'react'

/**
 * Lightbox for an image content attachment. Content-attachment URLs are public, non-expiring,
 * signed `/api/files/...` paths (Task 025) served same-origin with no auth header needed, so
 * unlike `SubmissionAttachmentPreview` this can point `<img>` straight at the URL instead of
 * fetching an authenticated blob first.
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
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  return (
    <div
      className='submission-preview'
      role='dialog'
      aria-modal='true'
      aria-label={`Предпросмотр ${name}`}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}>
      <section className='submission-preview__dialog'>
        <header className='submission-preview__header'>
          <div>
            <strong>{name}</strong>
          </div>
          <button className='btn btn-ghost btn-icon' type='button' aria-label='Закрыть предпросмотр' onClick={onClose}>
            ×
          </button>
        </header>
        <div className='submission-preview__body'>
          <img src={url} alt={name} />
        </div>
      </section>
    </div>
  )
}
