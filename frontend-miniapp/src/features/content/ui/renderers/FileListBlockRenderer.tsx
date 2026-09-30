import { useState } from 'react'

import type { BlockRendererProps, FileListBlock } from '@/entities/content/model/types'
import { trackAnalyticsEventInBackground } from '@/features/analytics/api/analyticsApi'
import { ContentAttachmentPreview } from '@/features/content/ui/ContentAttachmentPreview'
import { downloadFile } from '@/max/bridge'

export function FileListBlockRenderer({ block, content }: BlockRendererProps<FileListBlock>) {
  const [previewItem, setPreviewItem] = useState<{ name: string; url: string } | null>(null)

  return (
    <div className='cms-files'>
      {block.items.map((item) => {
        const entry = content.attachment_urls[item.attachment_id]
        const url = entry ? window.location.origin + entry.url : null
        const isImage = Boolean(entry?.mime.startsWith('image/'))
        const key = `${item.attachment_id}-${item.title}`

        if (item.display_mode === 'inline_image' && isImage && url) {
          return <img key={key} className='cms-files__inline-image' src={url} alt={item.title} />
        }

        const download = () => {
          if (!url) return
          trackAnalyticsEventInBackground({
            action_type: 'content_block_interaction',
            interaction_kind: 'file_download',
            source_surface: 'category',
            category_id: content.id,
            content_version_id: content.version_id,
            block_id: block.id,
            attachment_id: item.attachment_id,
          })
          downloadFile(url, item.title)
        }

        return (
          <div className='cms-files__item' key={key}>
            {isImage && url ? (
              <button
                type='button'
                className='cms-files__thumb'
                aria-label={`Предпросмотр ${item.title}`}
                onClick={() => setPreviewItem({ name: item.title, url })}>
                <img src={url} alt='' />
              </button>
            ) : (
              <span className='cms-files__icon' aria-hidden='true'>
                ↓
              </span>
            )}
            <button type='button' className='cms-files__download' disabled={!url} onClick={download}>
              <span>
                <strong>{item.title}</strong>
                {item.description ? <small>{item.description}</small> : null}
              </span>
            </button>
          </div>
        )
      })}
      {previewItem ? (
        <ContentAttachmentPreview name={previewItem.name} url={previewItem.url} onClose={() => setPreviewItem(null)} />
      ) : null}
    </div>
  )
}
