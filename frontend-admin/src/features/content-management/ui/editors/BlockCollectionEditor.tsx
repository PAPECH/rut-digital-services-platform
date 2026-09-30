import type { ContentBlock } from "@/entities/content/model/types";
import {
  blockLabels,
  createBlock,
} from "@/features/content-management/lib/blockFactory";
import { BlockEditorRegistry } from "./BlockEditorRegistry";
import { BlockTypePicker } from "./BlockTypePicker";

export function BlockCollectionEditor({
  blocks,
  onChange,
}: {
  blocks: ContentBlock[];
  onChange: (blocks: ContentBlock[]) => void;
}) {
  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= blocks.length) return;
    const next = [...blocks];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };

  return (
    <div className="content-block-list">
      {blocks.length === 0 ? (
        <div className="content-empty-state">
          <strong>Страница пока пустая</strong>
          <span>Добавьте первый визуальный блок.</span>
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
                onClick={() =>
                  onChange(blocks.filter((item) => item.id !== block.id))
                }
              >
                Удалить
              </button>
            </div>
          </header>
          <BlockEditorRegistry
            block={block}
            onChange={(updated) =>
              onChange(
                blocks.map((item) => (item.id === block.id ? updated : item)),
              )
            }
          />
        </section>
      ))}
      <BlockTypePicker
        allowTabs
        excludeTypes={blocks
          .filter(
            (block) =>
              block.type === "form_catalog" ||
              block.type === "submission_history" ||
              block.type === "faq_list" ||
              block.type === "news_list",
          )
          .map((block) => block.type)}
        onAdd={(type) => onChange([...blocks, createBlock(type)])}
      />
    </div>
  );
}
