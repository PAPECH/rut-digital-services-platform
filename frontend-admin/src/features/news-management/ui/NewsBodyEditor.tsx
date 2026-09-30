import type { NewsBodyBlock } from '@/entities/content/model/types'
import { blockLabels, createBlock } from '@/features/content-management/lib/blockFactory'
import { BlockTypePicker } from '@/features/content-management/ui/editors/BlockTypePicker'
import { NestedBlockEditorRegistry } from '@/features/content-management/ui/editors/NestedBlockEditorRegistry'

// A news item's body is composed from the same content-shaping block types as a category page
// (heading/paragraph/callout/contact_list/link/file_list), reusing their editor components
// as-is -- but never the navigational ones (accordion/steps/form_action/capability_action, plus
// every page-level system block), which only make sense on a full category page.
const EXCLUDED_NESTED_TYPES = ['accordion', 'steps', 'form_action', 'capability_action'] as const

export function NewsBodyEditor({
  blocks,
  onChange,
}: {
  blocks: NewsBodyBlock[]
  onChange: (blocks: NewsBodyBlock[]) => void
}) {
  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction
    if (target < 0 || target >= blocks.length) return
    const next = [...blocks]
    ;[next[index], next[target]] = [next[target], next[index]]
    onChange(next)
  }

  return (
    <div className="content-block-list">
      {blocks.length === 0 ? (
        <div className="content-empty-state">
          <strong>Текст новости пока пустой</strong>
          <span>Добавьте первый блок.</span>
        </div>
      ) : null}
      {blocks.map((block, index) => (
        <section className="content-block-card" key={block.id}>
          <header className="content-block-card__head">
            <div>
              <strong>{blockLabels[block.type]}</strong>
              <code>{block.id}</code>
            </div>
            <div className="content-inline-actions">
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={index === 0}
                onClick={() => move(index, -1)}
                aria-label="Поднять блок"
              >
                ↑
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                disabled={index === blocks.length - 1}
                onClick={() => move(index, 1)}
                aria-label="Опустить блок"
              >
                ↓
              </button>
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={() => onChange(blocks.filter((item) => item.id !== block.id))}
              >
                Удалить
              </button>
            </div>
          </header>
          <NestedBlockEditorRegistry
            block={block}
            onChange={(updated) =>
              onChange(blocks.map((item) => (item.id === block.id ? (updated as NewsBodyBlock) : item)))
            }
          />
        </section>
      ))}
      <BlockTypePicker
        allowTabs={false}
        excludeTypes={[...EXCLUDED_NESTED_TYPES]}
        onAdd={(type) => onChange([...blocks, createBlock(type) as NewsBodyBlock])}
      />
    </div>
  )
}
