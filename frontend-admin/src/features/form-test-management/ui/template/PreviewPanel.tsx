import { useState } from "react";

import type { ResultFilter, ResultScale } from "@/entities/form-test/model/types";
import { formTestApi } from "@/features/form-test-management/api/formTestApi";
import * as styles from "./PreviewPanel.css";

export function PreviewPanel({
  testId,
  resultScales,
  filters,
  resultTemplate,
}: {
  testId: number;
  resultScales: ResultScale[];
  filters: ResultFilter[];
  resultTemplate: string;
}) {
  const [sampleValues, setSampleValues] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ rendered_text: string; chunks: string[] } | null>(null);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      const values: Record<string, number> = {};
      for (const scale of resultScales) {
        const raw = sampleValues[scale.key];
        values[scale.key] = raw === undefined || raw === "" ? 0 : Number(raw);
      }
      const response = await formTestApi.preview(testId, {
        filters,
        result_template: resultTemplate,
        sample_values: values,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось построить предпросмотр");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.head}>
        <span>Тестовые значения шкал для предпросмотра</span>
        <button type="button" className="btn btn-secondary btn-sm" disabled={busy} onClick={() => void run()}>
          {busy ? "Считаем…" : "Предпросмотр"}
        </button>
      </div>
      {resultScales.length > 0 && (
        <div className={styles.grid}>
          {resultScales.map((scale) => (
            <label key={scale.key} className={styles.field}>
              <span>{scale.label || scale.key}</span>
              <input
                className="input"
                type="number"
                value={sampleValues[scale.key] ?? ""}
                onChange={(e) =>
                  setSampleValues((current) => ({ ...current, [scale.key]: e.target.value }))
                }
              />
            </label>
          ))}
        </div>
      )}
      {error && <div className={styles.error}>{error}</div>}
      {result && (
        <div className={styles.result}>
          <div className={styles.resultMeta}>
            Итоговое сообщение: {result.chunks.length} часть(ей)
            {result.chunks.length > 1 ? " — превышает лимит MAX в 4000 символов" : ""}
          </div>
          {result.chunks.map((chunk, index) => (
            <pre key={index} className={styles.chunk}>
              {chunk}
            </pre>
          ))}
        </div>
      )}
    </div>
  );
}
