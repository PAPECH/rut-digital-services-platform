import type { CheckboxField } from "@/entities/form/model/types";
import type { FieldPreviewProps } from "./previewTypes";
import * as styles from "./FieldPreview.css";

export function CheckboxFieldPreview({
  field,
}: FieldPreviewProps<CheckboxField>) {
  return (
    <label className={styles.checkboxRow}>
      <input className={styles.control} type="checkbox" disabled checked={field.default} readOnly />
      <span>
        {field.label}
        {field.required ? <span className={styles.required}> *</span> : null}
      </span>
    </label>
  );
}
