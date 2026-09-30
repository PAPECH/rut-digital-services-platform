import { useState } from 'react'
import type { AdminContentCategory, ContentDraft } from '@/entities/content/model/types'
import type { ContentIconName } from '@/entities/content/model/contentIcons'
import { ContentIconPicker } from '@/entities/content/ui/ContentIconPicker'
import { availableCategoryParents } from '../model/categoryTree'
import { BlockCollectionEditor } from './editors/BlockCollectionEditor'
import { useContentEditorResources } from '@/features/content-management/model/ContentEditorResourcesContext'
import { FilePickerModal } from '@/features/content-files/ui/FilePickerModal'

/**
 * Category `image_url` is only ever rendered as `<img src>` (see `ContentCategoryGrid.tsx`), never
 * offered as a download -- it needs `action=view` so the backend serves it with
 * `Content-Disposition: inline` instead of the default `attachment` used for file_list downloads.
 * `action` isn't part of the URL's HMAC signature (see `verify_signed`), so overwriting it here is
 * safe without a fresh signed URL from the server.
 */
function withViewAction(url: string): string {
  const [path, query = ''] = url.split('?')
  const params = new URLSearchParams(query)
  params.set('action', 'view')
  return `${path}?${params.toString()}`
}

export function ContentDraftEditor({
  category,
  draft,
  categories,
  onChange,
  onIconChange,
  onParentChange,
}: {
  category: AdminContentCategory
  draft: ContentDraft
  categories: AdminContentCategory[]
  onChange: (draft: ContentDraft) => void
  onIconChange: (icon: ContentIconName) => void
  onParentChange: (parentId: number | null) => void
}) {
  const parentOptions = availableCategoryParents(categories, category.id)

  const { registerAttachment } = useContentEditorResources()

  const [pickerOpen, setPickerOpen] = useState(false)

  const handleRemove = () => {
    onChange({
      ...draft,
      image_url: null,
    })
  }

  const previewUrl = draft.image_url

  return (
    <div className='content-draft-editor'>
      <section className='content-meta-editor'>
        {category.is_home ? (
          <div className='content-editor-grid'>
            <label className='content-checkbox capability-checkbox'>
              <span className='field-label'>Приветствие</span>
              <div className='capability-checkbox-control'>
                <input
                  type='checkbox'
                  checked={draft.header_visible}
                  onChange={(event) =>
                    onChange({
                      ...draft,
                      header_visible: event.target.checked,
                    })
                  }
                />
                Показывать заголовок и подзаголовок на главном экране?
              </div>
            </label>

            <label>
              <span className='field-label'>Язык</span>
              <select
                className='select'
                value={draft.language}
                onChange={(event) =>
                  onChange({
                    ...draft,
                    language: event.target.value,
                  })
                }>
                <option value='ru'>Русский</option>
                <option value='en'>English</option>
              </select>
            </label>

            <label className='content-editor-wide'>
              <span className='field-label'>Заголовок приветствия</span>
              <input
                className='input'
                maxLength={300}
                value={draft.title}
                onChange={(event) =>
                  onChange({
                    ...draft,
                    title: event.target.value,
                  })
                }
              />
            </label>

            <label className='content-editor-wide'>
              <span className='field-label'>Текст приветствия</span>

              <textarea
                className='textarea'
                rows={2}
                maxLength={2000}
                value={draft.subtitle ?? ''}
                onChange={(event) =>
                  onChange({
                    ...draft,
                    subtitle: event.target.value || null,
                  })
                }
              />
            </label>

            <p className='muted content-editor-wide'>
              В заголовке и тексте приветствия можно подставить имя пользователя:{' '}
              <code>{'{{ profile.first_name }}'}</code>. Если имени нет, окружающая запятая
              уберётся сама.
            </p>
          </div>
        ) : (
          <div className='content-editor-grid'>
            <label>
              <span className='field-label'>Название карточки</span>
              <input
                className='input'
                maxLength={300}
                value={draft.title}
                onChange={(event) =>
                  onChange({
                    ...draft,
                    title: event.target.value,
                  })
                }
              />
            </label>

            <label>
              <span className='field-label'>Иконка карточки</span>
              <ContentIconPicker value={category.icon} onChange={onIconChange} />
            </label>

            <div>
              <span className='field-label'>Изображение категории</span>

              {previewUrl ? (
                <div className='content-file-preview'>
                  <img
                    src={previewUrl}
                    alt={draft.title}
                    height={'76px'}
                    width={'76px'}
                    className='content-file-preview-image'
                  />
                </div>
              ) : null}

              <div className='content-file-controls'>
                <button type='button' className='btn btn-secondary btn-sm' onClick={() => setPickerOpen(true)}>
                  {draft.image_url ? 'Заменить изображение' : 'Выбрать изображение'}
                </button>

                {draft.image_url ? (
                  <button type='button' className='btn btn-secondary btn-sm' onClick={handleRemove}>
                    Убрать
                  </button>
                ) : null}
              </div>

              {pickerOpen ? (
                <FilePickerModal
                  title='Изображение категории'
                  imageOnly
                  uploadPurpose='category_icon'
                  onUploaded={registerAttachment}
                  onPick={(attachment) =>
                    onChange({
                      ...draft,
                      image_url: withViewAction(attachment.url),
                    })
                  }
                  onClose={() => setPickerOpen(false)}
                />
              ) : null}
            </div>

            <label className='content-checkbox capability-checkbox'>
              <span className='field-label'>Цвет карточки</span>
              <div className='capability-checkbox-control'>
                <input
                  type='checkbox'
                  checked={draft.is_filled}
                  onChange={(event) =>
                    onChange({
                      ...draft,
                      is_filled: event.target.checked,
                    })
                  }
                />
                Заполнить карточку цветом системы?
              </div>
            </label>

            <label>
              <span className='field-label'>Язык</span>
              <select
                className='select'
                value={draft.language}
                onChange={(event) =>
                  onChange({
                    ...draft,
                    language: event.target.value,
                  })
                }>
                <option value='ru'>Русский</option>
                <option value='en'>English</option>
              </select>
            </label>

            <label>
              <span className='field-label'>Родительская категория</span>

              <select
                className='select'
                value={category.parent_id ?? ''}
                onChange={(event) => onParentChange(event.target.value ? Number(event.target.value) : null)}>
                <option value=''>Корневая категория</option>

                {parentOptions.map((parent) => (
                  <option value={parent.id} key={parent.id}>
                    {parent.draft?.title ?? parent.slug} (/{parent.slug})
                  </option>
                ))}
              </select>
            </label>

            <label className='content-editor-wide'>
              <span className='field-label'>Краткое описание</span>

              <textarea
                className='textarea'
                rows={2}
                maxLength={2000}
                value={draft.subtitle ?? ''}
                onChange={(event) =>
                  onChange({
                    ...draft,
                    subtitle: event.target.value || null,
                  })
                }
              />
            </label>
          </div>
        )}

        <div className='content-meta-line'>
          <code>/{category.slug}</code>
          <span>ревизия {draft.revision}</span>
        </div>
      </section>

      <BlockCollectionEditor
        blocks={draft.blocks}
        onChange={(blocks) =>
          onChange({
            ...draft,
            blocks,
          })
        }
      />
    </div>
  )
}
