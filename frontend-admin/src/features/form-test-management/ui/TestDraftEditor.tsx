import { useRef } from "react";

import type { ConsentDocumentSummary, TestDraft } from "@/entities/form-test/model/types";
import { ElementListEditor } from "./elements/ElementListEditor";
import { ResultScaleListEditor } from "./scales/ResultScaleListEditor";
import { FilterListEditor } from "./filters/FilterListEditor";
import { ResultTemplateEditor } from "./template/ResultTemplateEditor";
import { ConsentSection } from "./consent/ConsentSection";
import { AttemptSettingsSection } from "./settings/AttemptSettingsSection";
import * as styles from "./TestDraftEditor.css";

export function TestDraftEditor({
  testId,
  draft,
  onChange,
  busy,
  error,
  notice,
  lastPublishedRevision,
  consentDocuments,
  onSave,
  onPublish,
  onExport,
  onImport,
}: {
  testId: number;
  draft: TestDraft;
  onChange: (draft: TestDraft) => void;
  busy: "save" | "publish" | "export" | "import" | null;
  error: string | null;
  notice: string | null;
  lastPublishedRevision: number;
  consentDocuments: ConsentDocumentSummary[];
  onSave: () => void;
  onPublish: () => void;
  onExport: () => void;
  onImport: (file: File) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const canPublish = draft.revision > lastPublishedRevision;

  return (
    <div className="card">
      <div className="card-body">
        <div className={styles.toolbar}>
          <div>
            <h2 className={styles.title}>{draft.name || "Без названия"}</h2>
            <span className={styles.meta}>
              редакция {draft.revision}
              {draft.updated_at ? ` · сохранено ${new Date(draft.updated_at).toLocaleString("ru-RU")}` : ""}
            </span>
          </div>
          <div className={styles.actions}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              className={styles.hiddenInput}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) onImport(file);
                event.target.value = "";
              }}
            />
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled={busy != null}
              onClick={() => fileInputRef.current?.click()}
            >
              {busy === "import" ? "Загружаем файл…" : "Импорт .xlsx"}
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled={busy != null}
              onClick={onExport}
            >
              {busy === "export" ? "Готовим файл…" : "Экспорт .xlsx"}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={busy != null}
              onClick={onSave}
            >
              {busy === "save" ? "Сохранение…" : "Сохранить черновик"}
            </button>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={busy != null || !canPublish}
              onClick={onPublish}
            >
              {busy === "publish" ? "Публикация…" : "Опубликовать"}
            </button>
          </div>
        </div>

        {error && <div className={styles.errorBanner}>{error}</div>}
        {notice && <div className={styles.noticeBanner}>{notice}</div>}

        <div className={styles.metaFields}>
          <label className={styles.field}>
            <span>Название теста</span>
            <input
              className="input"
              value={draft.name}
              onChange={(event) => onChange({ ...draft, name: event.target.value })}
            />
          </label>
          <label className={styles.field}>
            <span>Вводный текст (показывается перед началом теста)</span>
            <textarea
              className="input"
              rows={2}
              value={draft.intro_text ?? ""}
              onChange={(event) => onChange({ ...draft, intro_text: event.target.value || null })}
            />
          </label>
        </div>

        <div className={styles.mobileNotice}>
          Структуру теста удобнее редактировать на широком экране — на телефоне доступны все
          поля, но верстка компактнее.
        </div>

        <div className={styles.section}>
          <ElementListEditor
            elements={draft.test_schema.elements}
            onChange={(elements) =>
              onChange({ ...draft, test_schema: { ...draft.test_schema, elements } })
            }
          />
        </div>

        <div className={styles.section}>
          <ResultScaleListEditor
            elements={draft.test_schema.elements}
            resultScales={draft.test_schema.result_scales}
            onChange={(result_scales) =>
              onChange({ ...draft, test_schema: { ...draft.test_schema, result_scales } })
            }
          />
        </div>

        <div className={styles.section}>
          <h3>Интерпретация результатов</h3>
          <FilterListEditor
            resultScales={draft.test_schema.result_scales}
            filters={draft.test_schema.filters}
            onChange={(filters) =>
              onChange({ ...draft, test_schema: { ...draft.test_schema, filters } })
            }
          />
        </div>

        <div className={styles.section}>
          <ResultTemplateEditor
            testId={testId}
            resultTemplate={draft.test_schema.result_template}
            resultScales={draft.test_schema.result_scales}
            filters={draft.test_schema.filters}
            onChange={(result_template) =>
              onChange({ ...draft, test_schema: { ...draft.test_schema, result_template } })
            }
          />
        </div>

        <div className={styles.section}>
          <ConsentSection
            draft={draft}
            documents={consentDocuments}
            onChange={(patch) => onChange({ ...draft, ...patch })}
          />
        </div>

        <div className={styles.section}>
          <AttemptSettingsSection draft={draft} onChange={(patch) => onChange({ ...draft, ...patch })} />
        </div>
      </div>
    </div>
  );
}
