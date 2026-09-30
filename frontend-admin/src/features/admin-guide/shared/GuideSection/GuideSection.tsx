import type { ReactNode } from "react";

import * as styles from "./GuideSection.css";

export interface GuideSectionLink {
  id: string;
  title: string;
}

export function GuideSection({
  id,
  title,
  lead,
  children,
}: GuideSectionLink & { lead?: ReactNode; children: ReactNode }) {
  return (
    <section id={id} className={styles.section} aria-labelledby={`${id}-title`}>
      <h2 id={`${id}-title`} className={styles.title}>
        {title}
      </h2>
      {lead ? <p className={styles.lead}>{lead}</p> : null}
      {children}
    </section>
  );
}
