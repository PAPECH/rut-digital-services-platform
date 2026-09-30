import type { FormTestElement } from "@/entities/form-test/model/types";
import { QuestionFrame } from "./QuestionFrame";
import * as styles from "./TextQuestionInput.css";

export function TextQuestionInput({
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
  return (
    <QuestionFrame element={element} number={number}>
      <input
        className={`input ${styles.input}`}
        type="text"
        disabled={disabled}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
      />
    </QuestionFrame>
  );
}
