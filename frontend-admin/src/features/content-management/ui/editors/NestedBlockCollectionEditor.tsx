import type {
  NestedContentBlock,
  NestedContentBlockType,
} from "@/entities/content/model/types";
import {
  blockLabels,
  createNestedBlock,
} from "@/features/content-management/lib/blockFactory";
import { BlockTypePicker } from "./BlockTypePicker";
import { NestedBlockEditorRegistry } from "./NestedBlockEditorRegistry";

export function NestedBlockCollectionEditor({
  blocks,
  onChange,
}: {
  blocks: NestedContentBlock[];
  onChange: (blocks: NestedContentBlock[]) => void;
}) {
  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= blocks.length) return;
    const next = [...blocks];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };

  return (
    <div className="content-nested-blocks">
      {blocks.length === 0 ? (
        <p className="muted">Во вкладке пока нет блоков.</p>
      ) : null}
      {blocks.map((block, index) => (
        <section
          className="content-block-card content-block-card--nested"
          key={block.id}
        >
          <header className="content-block-card__head">
            <strong>{blockLabels[block.type]}</strong>
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
          <NestedBlockEditorRegistry
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
        allowTabs={false}
        onAdd={(type) =>
          onChange([
            ...blocks,
            createNestedBlock(type as NestedContentBlockType),
          ])
        }
      />
    </div>
  );
}
