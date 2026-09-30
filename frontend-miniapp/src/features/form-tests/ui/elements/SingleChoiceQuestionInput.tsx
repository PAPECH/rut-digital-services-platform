import type { FormTestElement } from "@/entities/form-test/model/types";
import { QuestionFrame } from "./QuestionFrame";
import * as styles from "./SingleChoiceQuestionInput.css";

export function SingleChoiceQuestionInput({
  element,
  number,
  value,
  disabled,
  onChange,
}: {
  element: FormTestElement;
  number: number | undefined;
  value: string | undefined;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  const options = element.options ?? [];
  return (
    <QuestionFrame element={element} number={number}>
      <div className={styles.list}>
        {options.map((option) => (
          <label key={option.value} className={styles.option}>
            <input
              className={styles.input}
              type="radio"
              name={element.key}
              disabled={disabled}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            {option.label}
          </label>
        ))}
      </div>
    </QuestionFrame>
  );
}
