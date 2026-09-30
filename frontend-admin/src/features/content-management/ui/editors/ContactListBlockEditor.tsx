import type {
  BlockEditorProps,
  ContactListBlock,
} from "@/entities/content/model/types";
import { EditorField, ItemActions } from "./EditorFields";

export function ContactListBlockEditor({
  block,
  onChange,
}: BlockEditorProps<ContactListBlock>) {
  const patchItem = (
    index: number,
    patch: Partial<ContactListBlock["items"][number]>,
  ) => {
    onChange({
      ...block,
      items: block.items.map((item, itemIndex) =>
        itemIndex === index ? { ...item, ...patch } : item,
      ),
    });
  };
  return (
    <div className="content-repeater">
      {block.items.map((item, index) => (
        <div className="content-repeater-item" key={`${block.id}-${index}`}>
          <div className="content-editor-grid">
            <EditorField label="Подпись">
              <input
                className="input"
                value={item.label}
                onChange={(event) =>
                  patchItem(index, { label: event.target.value })
                }
              />
            </EditorField>
            <EditorField label="Значение">
              <input
                className="input"
                value={item.value}
                onChange={(event) =>
                  patchItem(index, { value: event.target.value })
                }
              />
            </EditorField>
            <div className="content-editor-wide">
              <EditorField label="Ссылка (tel:, mailto: или https://)">
                <input
                  className="input"
                  value={item.href ?? ""}
                  onChange={(event) =>
                    patchItem(index, { href: event.target.value || null })
                  }
                />
              </EditorField>
            </div>
          </div>
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
        addLabel="Добавить контакт"
        onAdd={() =>
          onChange({
            ...block,
            items: [
              ...block.items,
              { label: "Контакт", value: "", href: null },
            ],
          })
        }
      />
    </div>
  );
}
