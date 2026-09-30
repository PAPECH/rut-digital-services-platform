import type { FormTestElement } from "@/entities/form-test/model/types";
import * as styles from "./QuestionnaireTitle.css";

export function QuestionnaireTitle({ element }: { element: FormTestElement }) {
  return <h2 className={styles.title}>{element.label}</h2>;
}
