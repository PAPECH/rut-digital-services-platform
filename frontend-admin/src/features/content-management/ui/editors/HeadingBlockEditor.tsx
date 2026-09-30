import type { BlockEditorProps, HeadingBlock } from '@/entities/content/model/types'
import { EditorField } from './EditorFields'

export function HeadingBlockEditor({ block, onChange }: BlockEditorProps<HeadingBlock>) {
  return (
    <div className='content-editor-grid'>
      <EditorField label='Текст заголовка'>
        <input
          className='input'
          value={block.text}
          onChange={(event) => onChange({ ...block, text: event.target.value })}
        />
      </EditorField>
      <EditorField label='Уровень'>
        <select
          className='select'
          value={block.level}
          onChange={(event) => onChange({ ...block, level: Number(event.target.value) as 2 | 3 })}>
          <option value={1}>H1 - заголовок экрана</option>
          <option value={2}>H2 — основной</option>
          <option value={3}>H3 — дополнительный</option>
          <option value={4}>H4 — дополнительный</option>
          <option value={5}>H5 — дополнительный</option>
          <option value={6}>H6 — дополнительный</option>
        </select>
      </EditorField>
    </div>
  )
}
