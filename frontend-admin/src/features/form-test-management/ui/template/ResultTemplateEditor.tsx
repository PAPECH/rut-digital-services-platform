import { useRef } from "react";

import type { ResultFilter, ResultScale } from "@/entities/form-test/model/types";
import { unknownKeys } from "@/features/form-test-management/lib/templatePlaceholders";
import { PlaceholderPicker } from "./PlaceholderPicker";
import { PreviewPanel } from "./PreviewPanel";
import * as styles from "./ResultTemplateEditor.css";

export function ResultTemplateEditor({
  testId,
  resultTemplate,
  resultScales,
  filters,
  onChange,
}: {
  testId: number | null;
  resultTemplate: string;
  resultScales: ResultScale[];
  filters: ResultFilter[];
  onChange: (template: string) => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const knownKeys = new Set(resultScales.map((scale) => scale.key));
  const unresolved = unknownKeys(resultTemplate, knownKeys);

  const insertSnippet = (snippet: string) => {
    const el = textareaRef.current;
    const start = el?.selectionStart ?? resultTemplate.length;
    const end = el?.selectionEnd ?? resultTemplate.length;
    onChange(resultTemplate.slice(0, start) + snippet + resultTemplate.slice(end));
    requestAnimationFrame(() => {
      const cursor = start + snippet.length;
      el?.focus();
      el?.setSelectionRange(cursor, cursor);
    });
  };

  return (
    <div>
      <h3>Шаблон сообщения с результатом</h3>
      <p className={styles.hint}>
        Нажмите на кнопку ниже, чтобы вставить ссылку на шкалу — не нужно запоминать синтаксис
        плейсхолдеров. Блок «при риске» остаётся в сообщении только если по этой шкале сработал
        диапазон риска.
      </p>
      <PlaceholderPicker resultScales={resultScales} onInsert={insertSnippet} />
      <textarea
        ref={textareaRef}
        className="input"
        rows={10}
        value={resultTemplate}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Например: Ваш результат по шкале депрессии: (вставьте плейсхолдер кнопкой выше)"
      />
      {unresolved.length > 0 && (
        <p className={styles.warning}>
          Шаблон ссылается на несуществующие шкалы: {unresolved.join(", ")}. Проверьте ключи или
          удалите эти плейсхолдеры перед публикацией.
        </p>
      )}
      {testId != null && (
        <PreviewPanel
          testId={testId}
          resultScales={resultScales}
          filters={filters}
          resultTemplate={resultTemplate}
        />
      )}
    </div>
  );
}
