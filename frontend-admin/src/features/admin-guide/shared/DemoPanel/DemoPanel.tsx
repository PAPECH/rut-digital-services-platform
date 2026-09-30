import type { ReactNode } from "react";

import * as styles from "./DemoPanel.css";

export type DemoPanelKind = "steps" | "admin" | "result";

const LABELS: Record<DemoPanelKind, string> = {
  steps: "☰ Шаги — что делать",
  admin: "✎ В админке",
  result: "📱 Результат у пользователя",
};

/**
 * Labelled area of a guide demo, so it is always clear which part is the schematic list of
 * steps, which is the admin screen, and where to look for the result.
 */
export function DemoPanel({
  kind,
  hint,
  children,
}: {
  kind: DemoPanelKind;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className={styles.panel}>
      <span className={`${styles.label} ${styles.labelTone[kind]}`}>{LABELS[kind]}</span>
      {hint ? <p className={styles.hint}>{hint}</p> : null}
      {children}
    </div>
  );
}
