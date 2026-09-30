import type { FormTestElement } from "@/entities/form-test/model/types";
import * as styles from "./SectionTitle.css";

export function SectionTitle({ element }: { element: FormTestElement }) {
  return <h3 className={styles.title}>{element.label}</h3>;
}
