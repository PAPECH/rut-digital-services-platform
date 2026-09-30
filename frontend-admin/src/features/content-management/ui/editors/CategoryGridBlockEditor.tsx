import type {
  BlockEditorProps,
  CategoryGridBlock,
} from "@/entities/content/model/types";
import { useContentEditorResources } from "@/features/content-management/model/ContentEditorResourcesContext";
import { EditorField } from "./EditorFields";

export function CategoryGridBlockEditor({
  block,
  onChange,
}: BlockEditorProps<CategoryGridBlock>) {
  const { categories, loading, error } = useContentEditorResources();
  const currentIsMissing =
    block.parent_id !== null &&
    !categories.some((category) => category.id === block.parent_id);
  return (
    <div className="content-editor-grid">
      <EditorField label="Родительская категория">
        <select
          className="select"
          value={block.parent_id ?? ""}
          disabled={loading}
          onChange={(event) =>
            onChange({
              ...block,
              parent_id: event.target.value ? Number(event.target.value) : null,
            })
          }
        >
          <option value="">Категории верхнего уровня</option>
          {currentIsMissing ? (
            <option value={block.parent_id ?? ""}>Недоступная категория #{block.parent_id}</option>
          ) : null}
          {categories.map((category) => (
            <option value={category.id} key={category.id}>{category.slug}</option>
          ))}
        </select>
        {error ? <small className="form-error">{error}</small> : null}
      </EditorField>
      <label className="content-editor-wide">
        <span className="field-label">Заголовок блока</span>
        <input
          className="input"
          maxLength={300}
          value={block.title ?? ""}
          placeholder="Оставьте пустым, чтобы скрыть заголовок"
          onChange={(event) =>
            onChange({ ...block, title: event.target.value || null })
          }
        />
      </label>
    </div>
  );
}
