import type {
  BlockEditorProps,
  FormActionBlock,
} from "@/entities/content/model/types";
import { useContentEditorResources } from "@/features/content-management/model/ContentEditorResourcesContext";
import { EditorField } from "./EditorFields";

export function FormActionBlockEditor({
  block,
  onChange,
}: BlockEditorProps<FormActionBlock>) {
  const { forms, loading, error } = useContentEditorResources();
  const currentIsMissing =
    Boolean(block.form_id) && !forms.some((form) => form.id === block.form_id);
  return (
    <div className="content-editor-grid">
      <EditorField label="Форма">
        <select
          className="select"
          value={block.form_id}
          disabled={loading}
          onChange={(event) =>
            onChange({ ...block, form_id: Number(event.target.value) })
          }
        >
          <option value={0}>Выберите форму</option>
          {currentIsMissing ? (
            <option value={block.form_id}>Недоступная форма #{block.form_id}</option>
          ) : null}
          {forms.map((form) => (
            <option value={form.id} key={form.id}>{form.name}</option>
          ))}
        </select>
        {error ? <small className="form-error">{error}</small> : null}
      </EditorField>
      <EditorField label="Текст кнопки">
        <input
          className="input"
          value={block.title}
          onChange={(event) =>
            onChange({ ...block, title: event.target.value })
          }
        />
      </EditorField>
      <div className="content-editor-wide">
        <EditorField label="Описание">
          <textarea
            className="textarea"
            rows={2}
            value={block.description ?? ""}
            onChange={(event) =>
              onChange({ ...block, description: event.target.value || null })
            }
          />
        </EditorField>
      </div>
    </div>
  );
}
