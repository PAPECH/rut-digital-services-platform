import type { FormTestElement } from "@/entities/form-test/model/types";
import * as styles from "./Instruction.css";

export function Instruction({ element }: { element: FormTestElement }) {
  return <p className={styles.text}>{element.label}</p>;
}
