import type { RadioField } from "@/entities/form/model/types";
import { PreviewLabel, type FieldPreviewProps } from "./previewTypes";
import * as styles from "./FieldPreview.css";

export function RadioFieldPreview({ field }: FieldPreviewProps<RadioField>) {
  return (
    <fieldset className={styles.fieldset}>
      <PreviewLabel field={field} />
      <div className={styles.choiceList}>
        {field.options.map((o) => (
          <label className={styles.choice} key={o.value}>
            <input
              type="radio"
              disabled
              checked={field.default === o.value}
              readOnly
            />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
