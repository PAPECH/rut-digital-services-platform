import type { ResultFilter, ResultScale } from "@/entities/form-test/model/types";
import { FilterRow } from "./FilterRow";
import * as styles from "./FilterListEditor.css";

export function FilterListEditor({
  resultScales,
  filters,
  onChange,
}: {
  resultScales: ResultScale[];
  filters: ResultFilter[];
  onChange: (filters: ResultFilter[]) => void;
}) {
  const filterByScale = new Map(filters.map((filter) => [filter.result_scale_key, filter]));

  const replace = (scaleKey: string, filter: ResultFilter) =>
    onChange(
      filterByScale.has(scaleKey)
        ? filters.map((item) => (item.result_scale_key === scaleKey ? filter : item))
        : [...filters, filter],
    );

  if (resultScales.length === 0) {
    return (
      <div className={styles.empty}>
        Интерпретации доступны после того, как появится хотя бы одна расчётная шкала
      </div>
    );
  }

  return (
    <div className={styles.list}>
      {resultScales.map((scale) => {
        const filter = filterByScale.get(scale.key);
        return filter ? (
          <FilterRow
            key={scale.key}
            scaleLabel={scale.label || scale.key}
            filter={filter}
            onChange={(updated) => replace(scale.key, updated)}
            onRemove={() =>
              onChange(filters.filter((item) => item.result_scale_key !== scale.key))
            }
          />
        ) : (
          <div className={styles.addRow} key={scale.key}>
            <span>{scale.label || scale.key} — без интерпретации</span>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() =>
                onChange([...filters, { result_scale_key: scale.key, rules: [] }])
              }
            >
              + добавить интерпретацию
            </button>
          </div>
        );
      })}
    </div>
  );
}
