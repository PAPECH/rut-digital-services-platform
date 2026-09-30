import type { ReactNode } from "react";

import { useInView } from "../../model/useInView";
import { InteractiveBadge } from "../InteractiveBadge/InteractiveBadge";
import { reveal, revealShown } from "../motion.css";
import * as styles from "./PhoneMockup.css";

/**
 * A phone-shaped frame for guide examples. The content is an admin-side mockup of what the
 * student sees in the mini-app; it fades in the first time it scrolls into view.
 */
export function PhoneMockup({
  title = "Мини-приложение",
  interactive = false,
  children,
  className,
}: {
  title?: string;
  /** Shows «👆 Можно нажимать» in the bar; leave off for static pictures. */
  interactive?: boolean;
  children: ReactNode;
  className?: string;
}) {
  const { ref, inView } = useInView<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={[styles.frame, reveal, inView ? revealShown : "", className ?? ""].join(" ")}
      aria-label={`Пример: ${title}`}
    >
      <div className={styles.bar}>
        <span>{title}</span>
        {interactive ? <InteractiveBadge /> : <span aria-hidden>•••</span>}
      </div>
      <div className={styles.screen}>{children}</div>
    </div>
  );
}
