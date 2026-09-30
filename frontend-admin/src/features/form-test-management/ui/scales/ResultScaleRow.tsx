import { useState } from "react";

import type { ResultScale, ResultScaleTerm } from "@/entities/form-test/model/types";
import * as styles from "./ResultScaleRow.css";

export function ResultScaleRow({
  scale,
  index,
  isFirst,
  isLast,
  scoringKeys,
  otherScaleKeys,
  onChange,
  onMove,
  onDelete,
}: {
  scale: ResultScale;
  index: number;
  isFirst: boolean;
  isLast: boolean;
  scoringKeys: string[];
  otherScaleKeys: string[];
  onChange: (scale: ResultScale) => void;
  onMove: (direction: -1 | 1) => void;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const referenceOptions = [
    ...scoringKeys.map((key) => ({ key, group: "Вопрос" as const })),
    ...otherScaleKeys.map((key) => ({ key, group: "Шкала" as const })),
  ];

  const replaceTerm = (termIndex: number, term: ResultScaleTerm) =>
    onChange({
      ...scale,
      terms: scale.terms.map((item, current) => (current === termIndex ? term : item)),
    });

  return (
    <section className={styles.row}>
      <header className={styles.header}>
        <div className={styles.identity}>
          <span className={styles.number}>{index + 1}</span>
          <strong>{scale.label.trim() || `Шкала ${index + 1}`}</strong>
          <span className={styles.meta}>{scale.terms.length} терм(ов)</span>
        </div>
        <div className={styles.actions}>
          <button type="button" className="btn btn-ghost btn-sm" disabled={isFirst} onClick={() => onMove(-1)} aria-label="Поднять">↑</button>
          <button type="button" className="btn btn-ghost btn-sm" disabled={isLast} onClick={() => onMove(1)} aria-label="Опустить">↓</button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "Свернуть" : "Настроить"}
          </button>
          <button type="button" className="btn btn-danger btn-sm" onClick={onDelete}>Удалить</button>
        </div>
      </header>
      {expanded && (
        <div className={styles.settings}>
          <label className={styles.field}>
            <span>Ключ шкалы</span>
            <input className="input" value={scale.key} onChange={(e) => onChange({ ...scale, key: e.target.value })} />
          </label>
          <label className={styles.field}>
            <span>Название</span>
            <input className="input" value={scale.label} onChange={(e) => onChange({ ...scale, label: e.target.value })} />
          </label>
          <div className={styles.row2}>
            <label className={styles.field}>
              <span>Константа</span>
              <input
                className="input"
                type="number"
                value={scale.constant}
                onChange={(e) => onChange({ ...scale, constant: Number(e.target.value) || 0 })}
              />
            </label>
            <label className={styles.field}>
              <span>Агрегация</span>
              <select
                className="select"
                value={scale.aggregation}
                onChange={(e) => onChange({ ...scale, aggregation: e.target.value as "sum" | "mean" })}
              >
                <option value="sum">Сумма</option>
                <option value="mean">Среднее</option>
              </select>
            </label>
          </div>

          <div className={styles.termsHead}>
            <span>Термы формулы</span>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() =>
                onChange({
                  ...scale,
                  terms: [
                    ...scale.terms,
                    { question_key: referenceOptions[0]?.key ?? null, result_scale_key: null, weight: 1 },
                  ],
                })
              }
            >
              Добавить терм
            </button>
          </div>
          {scale.terms.length === 0 && (
            <div className={styles.empty}>Нет термов — формула не будет ничего считать</div>
          )}
          {scale.terms.map((term, termIndex) => {
            const selected = term.question_key ?? term.result_scale_key ?? "";
            return (
              <div className={styles.termRow} key={termIndex}>
                <select
                  className="select"
                  value={selected}
                  onChange={(e) => {
                    const key = e.target.value;
                    const isScale = otherScaleKeys.includes(key);
                    replaceTerm(termIndex, {
                      question_key: isScale ? null : key || null,
                      result_scale_key: isScale ? key : null,
                      weight: term.weight,
                    });
                  }}
                >
                  <option value="">— выберите источник —</option>
                  {referenceOptions.map((option) => (
                    <option value={option.key} key={`${option.group}-${option.key}`}>
                      [{option.group}] {option.key}
                    </option>
                  ))}
                </select>
                <select
                  className="select"
                  value={term.weight}
                  onChange={(e) => replaceTerm(termIndex, { ...term, weight: Number(e.target.value) })}
                >
                  <option value={1}>+</option>
                  <option value={-1}>−</option>
                </select>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() =>
                    onChange({ ...scale, terms: scale.terms.filter((_, i) => i !== termIndex) })
                  }
                >
                  Удалить
                </button>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
