import type { ReactNode } from "react";

import type { FormTestElement } from "@/entities/form-test/model/types";
import * as styles from "./QuestionFrame.css";

export function QuestionFrame({
  element,
  number,
  children,
}: {
  element: FormTestElement;
  number: number | undefined;
  children: ReactNode;
}) {
  return (
    <div>
      <label className={styles.label}>
        {number != null ? `${number}) ` : ""}
        {element.label}
        {element.required ? <span className={styles.required}> *</span> : null}
      </label>
      {children}
    </div>
  );
}
