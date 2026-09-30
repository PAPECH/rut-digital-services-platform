import type {
  BlockEditorProps,
  StepsBlock,
  TitledItem,
} from "@/entities/content/model/types";
import { createItemId } from "@/features/content-management/lib/blockFactory";
import { EditorField, ItemActions } from "./EditorFields";

export function StepsBlockEditor({
  block,
  onChange,
}: BlockEditorProps<StepsBlock>) {
  const patchItem = (index: number, patch: Partial<TitledItem>) =>
    onChange({
      ...block,
      items: block.items.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patch } : item,
      ),
    });
  return (
    <div className="content-repeater">
      {block.items.map((item, index) => (
        <div className="content-repeater-item" key={item.id}>
          <EditorField label={`Шаг ${index + 1}`}>
            <input
              className="input"
              value={item.title}
              onChange={(event) =>
                patchItem(index, { title: event.target.value })
              }
            />
          </EditorField>
          <EditorField label="Описание">
            <textarea
              className="textarea"
              rows={3}
              value={item.text}
              onChange={(event) =>
                patchItem(index, { text: event.target.value })
              }
            />
          </EditorField>
          <ItemActions
            onRemove={
              block.items.length > 1
                ? () =>
                    onChange({
                      ...block,
                      items: block.items.filter(
                        (_, itemIndex) => itemIndex !== index,
                      ),
                    })
                : undefined
            }
          />
        </div>
      ))}
      <ItemActions
        addLabel="Добавить шаг"
        onAdd={() =>
          onChange({
            ...block,
            items: [
              ...block.items,
              {
                id: createItemId("step"),
                title: `Шаг ${block.items.length + 1}`,
                text: "Описание действия",
              },
            ],
          })
        }
      />
    </div>
  );
}
