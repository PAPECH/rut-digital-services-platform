import { useState } from "react";

import type { FormTestElement, FormTestElementType } from "@/entities/form-test/model/types";
import { createElement, duplicateElement } from "@/features/form-test-management/lib/elementFactory";
import { ELEMENT_TYPES } from "@/features/form-test-management/model/elementTypes";
import { ElementRow } from "./ElementRow";
import * as styles from "./ElementListEditor.css";

const MAX_ELEMENTS = 1000;

export function ElementListEditor({
  elements,
  onChange,
}: {
  elements: FormTestElement[];
  onChange: (elements: FormTestElement[]) => void;
}) {
  // Default collapsed (Task 078): a test can carry 200+ elements, and scrolling through the
  // whole list just to reach the constructor's other sections is painful at that size.
  const [expanded, setExpanded] = useState(false);
  const [pendingType, setPendingType] = useState<FormTestElementType | "">("");

  const replace = (index: number, element: FormTestElement) =>
    onChange(elements.map((item, current) => (current === index ? element : item)));
  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= elements.length) return;
    const next = [...elements];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };
  const addPending = () => {
    if (!pendingType) return;
    onChange([...elements, createElement(pendingType, elements)]);
    setPendingType("");
  };

  return (
    <div>
      <div className={styles.head}>
        <div>
          <h3>Вопросы и элементы ({elements.length})</h3>
          <span className={styles.hint}>До {MAX_ELEMENTS} элементов в тесте</span>
        </div>
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => setExpanded((value) => !value)}>
          {expanded ? "Свернуть список" : "Показать список"}
        </button>
      </div>
      {expanded && (
        <>
          {elements.length ? (
            <div className={styles.list}>
              {elements.map((element, index) => (
                <ElementRow
                  key={`${element.key}-${index}`}
                  element={element}
                  index={index}
                  isFirst={index === 0}
                  isLast={index === elements.length - 1}
                  onChange={(updated) => replace(index, updated)}
                  onMove={(direction) => move(index, direction)}
                  onDuplicate={() => {
                    const next = [...elements];
                    next.splice(index + 1, 0, duplicateElement(element, elements));
                    onChange(next);
                  }}
                  onDelete={() => onChange(elements.filter((_, current) => current !== index))}
                />
              ))}
            </div>
          ) : (
            <div className={styles.empty}>
              <strong>Пока нет элементов</strong>
              <span>Добавьте первый элемент ниже.</span>
            </div>
          )}
          <div className={styles.addRow}>
            <select
              className="select"
              value={pendingType}
              disabled={elements.length >= MAX_ELEMENTS}
              onChange={(event) => setPendingType(event.target.value as FormTestElementType | "")}
            >
              <option value="">Тип элемента…</option>
              {ELEMENT_TYPES.map((type) => (
                <option value={type.value} key={type.value}>{type.label}</option>
              ))}
            </select>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              disabled={!pendingType || elements.length >= MAX_ELEMENTS}
              onClick={addPending}
            >
              Добавить
            </button>
          </div>
        </>
      )}
    </div>
  );
}
