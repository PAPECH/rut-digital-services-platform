import { useState } from 'react'

import { fileExtension } from '@/api/files'
import { Icon } from '@/components/Icon'
import type { BlockEditorProps, FileListBlock } from '@/entities/content/model/types'
import { useContentEditorResources } from '@/features/content-management/model/ContentEditorResourcesContext'
import { FilePickerModal } from '@/features/content-files/ui/FilePickerModal'
import { ContentAttachmentPreview } from '@/features/content-files/ui/ContentAttachmentPreview'
import { EditorField, EditorFieldGroup, ItemActions } from './EditorFields'

export function FileListBlockEditor({ block, onChange }: BlockEditorProps<FileListBlock>) {
  const { attachments, registerAttachment } = useContentEditorResources()
  const [pickerIndex, setPickerIndex] = useState<number | null>(null)
  const [previewIndex, setPreviewIndex] = useState<number | null>(null)

  const patchItem = (index: number, patch: Partial<FileListBlock['items'][number]>) =>
    onChange({
      ...block,
      items: block.items.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)),
    })

  return (
    <div className='content-repeater'>
      {block.items.map((item, index) => {
        const attachment = attachments.find((candidate) => candidate.id === item.attachment_id)
        const isImage = Boolean(attachment?.mime.startsWith('image/'))

        return (
          <div className='content-repeater-item' key={`${block.id}-${index}`}>
            <div className='content-editor-grid'>
              <EditorFieldGroup label='Файл'>
                <div className='content-file-controls'>
                  {attachment ? (
                    isImage ? (
                      <button
                        type='button'
                        className='content-files-thumb'
                        aria-label={`Предпросмотр ${attachment.name}`}
                        onClick={() => setPreviewIndex(index)}>
                        <img src={attachment.url} alt='' />
                      </button>
                    ) : (
                      <div className='content-file-chip'>
                        <span className='content-file-chip__icon'>
                          <Icon.Paperclip />
                        </span>
                        <span className='content-file-chip__meta'>
                          <strong>{attachment.name}</strong>
                          {fileExtension(attachment.name) ? <span>{fileExtension(attachment.name)}</span> : null}
                        </span>
                      </div>
                    )
                  ) : null}
                  <button type='button' className='btn btn-secondary btn-sm' onClick={() => setPickerIndex(index)}>
                    {attachment
                      ? 'Заменить файл'
                      : item.attachment_id
                        ? `Недоступный файл #${item.attachment_id} — выбрать другой`
                        : 'Выбрать файл'}
                  </button>
                </div>
              </EditorFieldGroup>
              <EditorField label='Название'>
                <input
                  className='input'
                  value={item.title}
                  onChange={(event) => patchItem(index, { title: event.target.value })}
                />
              </EditorField>
              {isImage ? (
                <EditorField label='Отображение'>
                  <select
                    className='select'
                    value={item.display_mode}
                    onChange={(event) =>
                      patchItem(index, { display_mode: event.target.value as FileListBlock['items'][number]['display_mode'] })
                    }>
                    <option value='tile'>Файл для скачивания</option>
                    <option value='inline_image'>Изображение в тексте</option>
                  </select>
                </EditorField>
              ) : null}
              <div className='content-editor-wide'>
                <EditorField label='Описание'>
                  <textarea
                    className='textarea'
                    rows={2}
                    value={item.description ?? ''}
                    onChange={(event) =>
                      patchItem(index, {
                        description: event.target.value || null,
                      })
                    }
                  />
                </EditorField>
              </div>
              {item.display_mode === 'inline_image' && attachment ? (
                <div className='content-editor-wide content-file-preview'>
                  <img
                    src={attachment.url}
                    alt={item.title}
                    height={'76px'}
                    width={'76px'}
                    className='content-file-preview-image'
                  />
                </div>
              ) : null}
            </div>
            <ItemActions
              onRemove={
                block.items.length > 1
                  ? () =>
                      onChange({
                        ...block,
                        items: block.items.filter((_, itemIndex) => itemIndex !== index),
                      })
                  : undefined
              }
            />
            {pickerIndex === index ? (
              <FilePickerModal
                title='Файл для блока'
                onUploaded={registerAttachment}
                onPick={(picked) =>
                  patchItem(index, {
                    attachment_id: picked.id,
                    title: item.title || picked.name,
                    display_mode: picked.mime.startsWith('image/') ? item.display_mode : 'tile',
                  })
                }
                onClose={() => setPickerIndex(null)}
              />
            ) : null}
            {previewIndex === index && attachment ? (
              <ContentAttachmentPreview name={attachment.name} url={attachment.url} onClose={() => setPreviewIndex(null)} />
            ) : null}
          </div>
        )
      })}
      <ItemActions
        addLabel='Добавить файл'
        onAdd={() =>
          onChange({
            ...block,
            items: [...block.items, { attachment_id: 0, title: 'Документ', description: null, display_mode: 'tile' }],
          })
        }
      />
    </div>
  )
}
