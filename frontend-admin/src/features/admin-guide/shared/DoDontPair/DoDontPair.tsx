import type { ReactNode } from "react";

import * as styles from "./DoDontPair.css";

interface Side {
  example: ReactNode;
  caption: ReactNode;
}

/** «Правильно / Неправильно» side-by-side comparison; stacks on mobile. */
export function DoDontPair({ good, bad }: { good: Side; bad: Side }) {
  return (
    <div className={styles.pair}>
      <div className={`${styles.side} ${styles.sideTone.do}`}>
        <span className={`${styles.label} ${styles.labelTone.do}`}>✓ Правильно</span>
        {good.example}
        <p className={styles.caption}>{good.caption}</p>
      </div>
      <div className={`${styles.side} ${styles.sideTone.dont}`}>
        <span className={`${styles.label} ${styles.labelTone.dont}`}>✕ Неправильно</span>
        {bad.example}
        <p className={styles.caption}>{bad.caption}</p>
      </div>
    </div>
  );
}
