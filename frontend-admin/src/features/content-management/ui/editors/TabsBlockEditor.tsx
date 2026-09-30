import type {
  BlockEditorProps,
  TabsBlock,
} from "@/entities/content/model/types";
import { createItemId } from "@/features/content-management/lib/blockFactory";
import { EditorField, ItemActions } from "./EditorFields";
import { NestedBlockCollectionEditor } from "./NestedBlockCollectionEditor";

export function TabsBlockEditor({
  block,
  onChange,
}: BlockEditorProps<TabsBlock>) {
  const patchTab = (
    index: number,
    patch: Partial<TabsBlock["tabs"][number]>,
  ) => {
    onChange({
      ...block,
      tabs: block.tabs.map((tab, tabIndex) =>
        tabIndex === index ? { ...tab, ...patch } : tab,
      ),
    });
  };

  return (
    <div className="content-repeater">
      {block.tabs.map((tab, index) => (
        <section className="content-tab-editor" key={tab.key}>
          <div className="content-editor-grid">
            <EditorField label="Название вкладки">
              <input
                className="input"
                value={tab.title}
                onChange={(event) =>
                  patchTab(index, { title: event.target.value })
                }
              />
            </EditorField>
            <EditorField label="Стабильный ключ">
              <input
                className="input"
                value={tab.key}
                onChange={(event) =>
                  patchTab(index, {
                    key: event.target.value
                      .toLowerCase()
                      .replace(/[^a-z0-9_-]/g, "_"),
                  })
                }
              />
            </EditorField>
          </div>
          <NestedBlockCollectionEditor
            blocks={tab.blocks}
            onChange={(blocks) => patchTab(index, { blocks })}
          />
          <ItemActions
            onRemove={
              block.tabs.length > 1
                ? () =>
                    onChange({
                      ...block,
                      tabs: block.tabs.filter(
                        (_, tabIndex) => tabIndex !== index,
                      ),
                    })
                : undefined
            }
          />
        </section>
      ))}
      <ItemActions
        addLabel="Добавить вкладку"
        onAdd={() =>
          onChange({
            ...block,
            tabs: [
              ...block.tabs,
              {
                key: createItemId("tab").toLowerCase(),
                title: `Вкладка ${block.tabs.length + 1}`,
                blocks: [],
              },
            ],
          })
        }
      />
    </div>
  );
}
