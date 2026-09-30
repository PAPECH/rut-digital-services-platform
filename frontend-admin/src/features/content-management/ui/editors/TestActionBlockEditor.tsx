import type {
  BlockEditorProps,
  TestActionBlock,
} from "@/entities/content/model/types";
import { useContentEditorResources } from "@/features/content-management/model/ContentEditorResourcesContext";
import { EditorField } from "./EditorFields";

export function TestActionBlockEditor({
  block,
  onChange,
}: BlockEditorProps<TestActionBlock>) {
  const { tests, loading, error } = useContentEditorResources();
  const currentIsMissing =
    Boolean(block.test_id) && !tests.some((test) => test.id === block.test_id);
  return (
    <div className="content-editor-grid">
      <EditorField label="Тест">
        <select
          className="select"
          value={block.test_id}
          disabled={loading}
          onChange={(event) =>
            onChange({ ...block, test_id: Number(event.target.value) })
          }
        >
          <option value={0}>Выберите тест</option>
          {currentIsMissing ? (
            <option value={block.test_id}>Недоступный тест #{block.test_id}</option>
          ) : null}
          {tests.map((test) => (
            <option value={test.id} key={test.id}>{test.name}</option>
          ))}
        </select>
        {error ? <small className="form-error">{error}</small> : null}
        {block.test_id ? (
          <a
            className="content-editor-link"
            href={`/form-tests?testId=${block.test_id}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            Перейти к тесту →
          </a>
        ) : null}
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
