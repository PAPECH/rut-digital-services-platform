import type {
  BlockEditorProps,
  CalloutBlock,
  CalloutTone,
} from "@/entities/content/model/types";
import { RichTextEditor } from "../RichTextEditor";
import { EditorField, EditorFieldGroup } from "./EditorFields";

export function CalloutBlockEditor({
  block,
  onChange,
}: BlockEditorProps<CalloutBlock>) {
  return (
    <div className="content-editor-grid">
      <EditorField label="Заголовок (необязательно)">
        <input
          className="input"
          value={block.title ?? ""}
          onChange={(event) =>
            onChange({ ...block, title: event.target.value || null })
          }
        />
      </EditorField>
      <EditorField label="Стиль">
        <select
          className="select"
          value={block.tone}
          onChange={(event) =>
            onChange({ ...block, tone: event.target.value as CalloutTone })
          }
        >
          <option value="info">Информация</option>
          <option value="warning">Предупреждение</option>
          <option value="success">Успех</option>
          <option value="danger">Ошибка</option>
        </select>
      </EditorField>
      <div className="content-editor-wide">
        <EditorFieldGroup label="Текст">
          <RichTextEditor
            key={block.id}
            value={block.text}
            rows={4}
            onChange={(text) => onChange({ ...block, text })}
          />
        </EditorFieldGroup>
      </div>
    </div>
  );
}
