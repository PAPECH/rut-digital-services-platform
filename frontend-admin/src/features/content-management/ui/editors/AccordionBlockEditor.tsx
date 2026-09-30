import type {
  AccordionBlock,
  BlockEditorProps,
  TitledItem,
} from "@/entities/content/model/types";
import { createItemId } from "@/features/content-management/lib/blockFactory";
import { EditorField, ItemActions } from "./EditorFields";

export function AccordionBlockEditor({
  block,
  onChange,
}: BlockEditorProps<AccordionBlock>) {
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
          <EditorField label="Заголовок">
            <input
              className="input"
              value={item.title}
              onChange={(event) =>
                patchItem(index, { title: event.target.value })
              }
            />
          </EditorField>
          <EditorField label="Содержимое">
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
        addLabel="Добавить раздел"
        onAdd={() =>
          onChange({
            ...block,
            items: [
              ...block.items,
              {
                id: createItemId("item"),
                title: "Новый раздел",
                text: "Содержимое",
              },
            ],
          })
        }
      />
    </div>
  );
}
