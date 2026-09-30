import type {
  BlockEditorProps,
  LinkBlock,
} from "@/entities/content/model/types";
import { EditorField } from "./EditorFields";

export function LinkBlockEditor({
  block,
  onChange,
}: BlockEditorProps<LinkBlock>) {
  return (
    <div className="content-editor-grid">
      <EditorField label="Название">
        <input
          className="input"
          value={block.title}
          onChange={(event) =>
            onChange({ ...block, title: event.target.value })
          }
        />
      </EditorField>
      <EditorField label="Вид">
        <select
          className="select"
          value={block.style}
          onChange={(event) =>
            onChange({
              ...block,
              style: event.target.value as LinkBlock["style"],
            })
          }
        >
          <option value="button">Кнопка</option>
          <option value="card">Карточка</option>
        </select>
      </EditorField>
      <div className="content-editor-wide">
        <EditorField label="Ссылка">
          <input
            className="input"
            value={block.href}
            onChange={(event) =>
              onChange({ ...block, href: event.target.value })
            }
          />
        </EditorField>
      </div>
      <label className="content-checkbox">
        <input
          type="checkbox"
          checked={block.external}
          onChange={(event) =>
            onChange({ ...block, external: event.target.checked })
          }
        />
        Открывать как внешнюю ссылку
      </label>
    </div>
  );
}
