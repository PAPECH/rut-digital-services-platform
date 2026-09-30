import type { ReactNode } from "react";

import { InteractiveBadge } from "../InteractiveBadge/InteractiveBadge";
import * as styles from "./DemoStage.css";

/**
 * The "demonstration" frame: everything inside is a mock of the admin or of the mini-app, set off
 * from the surrounding instruction text by its own tint, border and header.
 */
export function DemoStage({
  interactive = false,
  children,
}: {
  interactive?: boolean;
  children: ReactNode;
}) {
  return (
    <div className={styles.stage}>
      <div className={styles.header}>
        <span className={styles.title}>▶ Демонстрация</span>
        {interactive ? <InteractiveBadge /> : null}
      </div>
      <div className={styles.body}>{children}</div>
    </div>
  );
}
