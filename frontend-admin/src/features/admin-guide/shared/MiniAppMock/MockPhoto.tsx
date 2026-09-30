import * as styles from "./MockPhoto.css";

/** Placeholder "photo" for mockups — fills its box; the caller sets size and radius. */
export function MockPhoto({ className }: { className?: string }) {
  return (
    <span className={`${styles.photo} ${className ?? ""}`} aria-hidden>
      <span className={styles.sun} />
      <svg className={styles.hills} viewBox="0 0 100 40" preserveAspectRatio="none">
        <path d="M0 40 L0 22 L22 8 L40 24 L58 6 L80 26 L100 14 L100 40 Z" fill="#6f9f7a" />
      </svg>
    </span>
  );
}
