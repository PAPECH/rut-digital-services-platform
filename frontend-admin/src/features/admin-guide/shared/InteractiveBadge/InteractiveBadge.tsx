import * as styles from "./InteractiveBadge.css";

/** Marks a demo or mockup that reacts to clicks; everything without it is a static picture. */
export function InteractiveBadge() {
  return <span className={styles.badge}>👆 Можно нажимать</span>;
}
