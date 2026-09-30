import type { ScaleMatrixGroup } from "@/features/form-tests/model/groupElements";
import * as styles from "./ScaleQuestionMatrix.css";

/**
 * Renders a run of consecutive `scale` questions sharing the same option labels as one
 * rating-row table (statement rows x shared option columns) instead of repeating the same
 * option list under every statement -- how 7 of the 8 source instruments are actually laid
 * out. Wrapped in a horizontally scrolling strip so it stays usable at mobile width without a
 * fixed wide table overflowing the screen (this is the primary student-facing surface, not
 * desktop-first).
 */
export function ScaleQuestionMatrix({
  group,
  numberByKey,
  values,
  disabled,
  onChange,
}: {
  group: ScaleMatrixGroup;
  numberByKey: Map<string, number>;
  values: Record<string, string | undefined>;
  disabled: boolean;
  onChange: (key: string, value: string) => void;
}) {
  return (
    <div className={styles.scroll}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th />
            {group.optionLabels.map((label, index) => (
              <th key={index} className={styles.optionHeaderCell}>
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {group.questions.map((question) => (
            <tr key={question.key}>
              <td className={styles.statementCell}>
                {numberByKey.get(question.key) != null ? `${numberByKey.get(question.key)}) ` : ""}
                {question.label}
                {question.required ? " *" : ""}
              </td>
              {(question.options ?? []).map((option) => (
                <td key={option.value} className={styles.optionCell}>
                  <input
                    className={styles.input}
                    type="radio"
                    name={question.key}
                    disabled={disabled}
                    checked={values[question.key] === option.value}
                    onChange={() => onChange(question.key, option.value)}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
