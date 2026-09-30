import { useState } from "react";

import type { FormTestElement, FormTestElementType } from "@/entities/form-test/model/types";
import { convertElementType } from "@/features/form-test-management/lib/elementFactory";
import { CHOICE_ELEMENT_TYPES, ELEMENT_TYPES, STRUCTURAL_ELEMENT_TYPE_SET } from "@/features/form-test-management/model/elementTypes";
import { ElementOptionsEditor } from "./ElementOptionsEditor";
import * as styles from "./ElementRow.css";

export function ElementRow({
  element,
  index,
  isFirst,
  isLast,
  onChange,
  onMove,
  onDuplicate,
  onDelete,
}: {
  element: FormTestElement;
  index: number;
  isFirst: boolean;
  isLast: boolean;
  onChange: (element: FormTestElement) => void;
  onMove: (direction: -1 | 1) => void;
  onDuplicate: () => void;
  onDelete: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const isStructural = STRUCTURAL_ELEMENT_TYPE_SET.has(element.type);
  const isChoice = CHOICE_ELEMENT_TYPES.has(element.type);

  return (
    <section className={styles.row}>
      <header className={styles.header}>
        <div className={styles.identity}>
          <span className={styles.number}>{index + 1}</span>
          <span>
            <strong>{element.label.trim() || `Элемент ${index + 1}`}</strong>
            <small className={styles.key}>{element.key}</small>
          </span>
        </div>
        <div className={styles.actions}>
          <button type="button" className="btn btn-ghost btn-sm" disabled={isFirst} onClick={() => onMove(-1)} aria-label="Поднять">↑</button>
          <button type="button" className="btn btn-ghost btn-sm" disabled={isLast} onClick={() => onMove(1)} aria-label="Опустить">↓</button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setExpanded((value) => !value)}>
            {expanded ? "Свернуть" : "Настроить"}
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onDuplicate}>Дублировать</button>
          <button type="button" className="btn btn-danger btn-sm" onClick={onDelete}>Удалить</button>
        </div>
      </header>
      {expanded && (
        <div className={styles.settings}>
          <label className={styles.field}>
            <span>Тип элемента</span>
            <select
              className="select"
              value={element.type}
              onChange={(event) =>
                onChange(convertElementType(element, event.target.value as FormTestElementType))
              }
            >
              {ELEMENT_TYPES.map((type) => (
                <option value={type.value} key={type.value}>{type.label}</option>
              ))}
            </select>
          </label>
          <label className={styles.field}>
            <span>Ключ</span>
            <input
              className="input"
              value={element.key}
              onChange={(event) => onChange({ ...element, key: event.target.value })}
            />
          </label>
          <label className={styles.field}>
            <span>Текст</span>
            <textarea
              className="input"
              rows={2}
              value={element.label}
              onChange={(event) => onChange({ ...element, label: event.target.value })}
            />
          </label>
          {!isStructural && (
            <>
              <label className={styles.checkbox}>
                <input
                  type="checkbox"
                  checked={element.required ?? false}
                  onChange={(event) => onChange({ ...element, required: event.target.checked })}
                />
                <span>Обязательный вопрос</span>
              </label>
              <label className={styles.field}>
                <span>Ключ для подсчёта (scoring_key)</span>
                <input
                  className="input"
                  placeholder="оставьте пустым, если вопрос не влияет на шкалы"
                  value={element.scoring_key ?? ""}
                  onChange={(event) =>
                    onChange({ ...element, scoring_key: event.target.value || null })
                  }
                />
              </label>
            </>
          )}
          {isChoice && (
            <ElementOptionsEditor
              options={element.options ?? []}
              onChange={(options) => onChange({ ...element, options })}
            />
          )}
        </div>
      )}
    </section>
  );
}
