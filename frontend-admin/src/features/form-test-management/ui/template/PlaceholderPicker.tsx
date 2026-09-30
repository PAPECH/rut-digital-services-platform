import type { ResultScale } from "@/entities/form-test/model/types";
import { flaggedBlockFor, placeholderFor } from "@/features/form-test-management/lib/templatePlaceholders";
import * as styles from "./PlaceholderPicker.css";

const FIELD_LABELS = {
  value: "значение",
  label: "вывод",
  recommendation: "рекомендация",
} as const;

export function PlaceholderPicker({
  resultScales,
  onInsert,
}: {
  resultScales: ResultScale[];
  onInsert: (snippet: string) => void;
}) {
  if (resultScales.length === 0) {
    return (
      <p className={styles.empty}>
        Плейсхолдеры появятся здесь, как только вы добавите хотя бы одну расчётную шкалу.
      </p>
    );
  }

  return (
    <div className={styles.wrapper}>
      {resultScales.map((scale) => (
        <div key={scale.key} className={styles.group}>
          <span className={styles.groupLabel}>{scale.label || scale.key}</span>
          <div className={styles.groupButtons}>
            {(Object.keys(FIELD_LABELS) as Array<keyof typeof FIELD_LABELS>).map((field) => (
              <button
                type="button"
                key={field}
                className="btn btn-ghost btn-sm"
                title={placeholderFor(scale.key, field)}
                onClick={() => onInsert(placeholderFor(scale.key, field))}
              >
                + {FIELD_LABELS[field]}
              </button>
            ))}
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              title={flaggedBlockFor(scale.key, "…")}
              onClick={() => onInsert(flaggedBlockFor(scale.key, "текст только при риске"))}
            >
              + блок «при риске»
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
