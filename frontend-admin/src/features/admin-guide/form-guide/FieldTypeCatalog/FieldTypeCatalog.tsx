import { FORM_FIELD_TYPES } from "@/features/form-management/model/fieldTypes";
import { FormFieldPreviewRegistry } from "@/features/form-management/ui/preview/FormFieldPreviewRegistry";

import { PhoneMockup } from "../../shared/PhoneMockup/PhoneMockup";
import { FIELD_GUIDE, sampleField } from "../model/fieldGuide";
import * as styles from "./FieldTypeCatalog.css";

/** All field types, in the builder's «Добавить поле…» order, each with the builder's own preview. */
export function FieldTypeCatalog() {
  return (
    <div className={styles.grid}>
      {FORM_FIELD_TYPES.map(({ value, label }) => {
        const field = sampleField(value);
        return (
          <article key={value} className={styles.card}>
            <h3 className={styles.name}>{label}</h3>
            <p className={styles.use}>{FIELD_GUIDE[value].use}</p>
            <div className={styles.preview}>
              <PhoneMockup title="Форма">
                <FormFieldPreviewRegistry field={field} />
                {field.help_text ? <span className={styles.help}>{field.help_text}</span> : null}
              </PhoneMockup>
            </div>
          </article>
        );
      })}
    </div>
  );
}
