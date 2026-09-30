import type { FormTestElement } from "@/entities/form-test/model/types";
import { QuestionFrame } from "./QuestionFrame";
import * as styles from "./MultipleChoiceQuestionInput.css";

export function MultipleChoiceQuestionInput({
  element,
  number,
  value,
  disabled,
  onChange,
}: {
  element: FormTestElement;
  number: number | undefined;
  value: string[] | undefined;
  disabled: boolean;
  onChange: (value: string[]) => void;
}) {
  const selected = new Set(value ?? []);
  const toggle = (optionValue: string) => {
    const next = new Set(selected);
    if (next.has(optionValue)) next.delete(optionValue);
    else next.add(optionValue);
    onChange([...next]);
  };
  const options = element.options ?? [];

  return (
    <QuestionFrame element={element} number={number}>
      <div className={styles.list}>
        {options.map((option) => (
          <label key={option.value} className={styles.option}>
            <input
              className={styles.input}
              type="checkbox"
              disabled={disabled}
              checked={selected.has(option.value)}
              onChange={() => toggle(option.value)}
            />
            {option.label}
          </label>
        ))}
      </div>
    </QuestionFrame>
  );
}
