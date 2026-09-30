import type { FormField } from "@/entities/form/model/types";
import * as styles from "./FieldPreview.css";

export interface FieldPreviewProps<T extends FormField = FormField> {
  field: T;
}

export function PreviewLabel({ field }: FieldPreviewProps) {
  return (
    <label className="field-label">
      {field.label}
      {field.required ? <span className={styles.required}> *</span> : null}
    </label>
  );
}
