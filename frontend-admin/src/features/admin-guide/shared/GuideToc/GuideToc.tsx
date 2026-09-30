import { useMemo } from "react";

import { useActiveSection } from "../../model/useActiveSection";
import type { GuideSectionLink } from "../GuideSection/GuideSection";
import * as styles from "./GuideToc.css";

/** Sticky section list on desktop; a horizontal chip row on narrow screens. */
export function GuideToc({ sections }: { sections: ReadonlyArray<GuideSectionLink> }) {
  const ids = useMemo(() => sections.map((section) => section.id), [sections]);
  const active = useActiveSection(ids);
  return (
    <nav className={styles.toc} aria-label="Содержание">
      {sections.map((section) => (
        <a
          key={section.id}
          href={`#${section.id}`}
          className={section.id === active ? `${styles.link} ${styles.linkActive}` : styles.link}
          onClick={(event) => {
            event.preventDefault();
            document.getElementById(section.id)?.scrollIntoView({ behavior: "smooth" });
          }}
        >
          {section.title}
        </a>
      ))}
    </nav>
  );
}
