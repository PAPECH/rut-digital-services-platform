import type { MultiselectField } from "@/entities/form/model/types";
import { PreviewLabel, type FieldPreviewProps } from "./previewTypes";
import * as styles from "./FieldPreview.css";

export function MultiselectFieldPreview({
  field,
}: FieldPreviewProps<MultiselectField>) {
  const defaultValues = field.default ?? [];
  return (
    <fieldset className={styles.fieldset}>
      <PreviewLabel field={field} />
      <div className={styles.choiceList}>
        {field.options.map((o) => (
          <label className={styles.choice} key={o.value}>
            <input
              type="checkbox"
              disabled
              checked={defaultValues.includes(o.value)}
              readOnly
            />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
