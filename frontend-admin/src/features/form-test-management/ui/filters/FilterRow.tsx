import { useState } from "react";

import type { FilterRule, ResultFilter } from "@/entities/form-test/model/types";
import * as styles from "./FilterRow.css";

export function FilterRow({
  scaleLabel,
  filter,
  onChange,
  onRemove,
}: {
  scaleLabel: string;
  filter: ResultFilter;
  onChange: (filter: ResultFilter) => void;
  onRemove: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const replaceRule = (index: number, rule: FilterRule) =>
    onChange({ ...filter, rules: filter.rules.map((item, current) => (current === index ? rule : item)) });

  return (
    <section className={styles.row}>
      <header className={styles.header}>
        <div>
          <strong>{scaleLabel}</strong>
          <span className={styles.meta}> — {filter.rules.length} диапазона(ов)</span>
        </div>
        <div className={styles.actions}>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "Свернуть" : "Настроить"}
          </button>
          <button type="button" className="btn btn-danger btn-sm" onClick={onRemove}>Убрать интерпретацию</button>
        </div>
      </header>
      {expanded && (
        <div className={styles.settings}>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() =>
              onChange({
                ...filter,
                rules: [
                  ...filter.rules,
                  { min: null, max: null, label: "", is_flagged: false, recommendation_text: null },
                ],
              })
            }
          >
            + диапазон
          </button>
          {filter.rules.map((rule, index) => (
            <div className={styles.ruleRow} key={index}>
              <div className={styles.ruleGrid}>
                <input
                  className="input"
                  type="number"
                  placeholder="от"
                  value={rule.min ?? ""}
                  onChange={(e) =>
                    replaceRule(index, { ...rule, min: e.target.value === "" ? null : Number(e.target.value) })
                  }
                />
                <input
                  className="input"
                  type="number"
                  placeholder="до"
                  value={rule.max ?? ""}
                  onChange={(e) =>
                    replaceRule(index, { ...rule, max: e.target.value === "" ? null : Number(e.target.value) })
                  }
                />
                <input
                  className="input"
                  placeholder="название диапазона"
                  value={rule.label}
                  onChange={(e) => replaceRule(index, { ...rule, label: e.target.value })}
                />
                <label className={styles.flagLabel}>
                  <input
                    type="checkbox"
                    checked={rule.is_flagged}
                    onChange={(e) => replaceRule(index, { ...rule, is_flagged: e.target.checked })}
                  />
                  <span>риск</span>
                </label>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() => onChange({ ...filter, rules: filter.rules.filter((_, i) => i !== index) })}
                >
                  Удалить
                </button>
              </div>
              <textarea
                className="input"
                rows={2}
                placeholder="текст рекомендации (необязательно)"
                value={rule.recommendation_text ?? ""}
                onChange={(e) =>
                  replaceRule(index, { ...rule, recommendation_text: e.target.value || null })
                }
              />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
