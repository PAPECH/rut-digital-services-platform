import type { ContentBlockType } from "@/entities/content/model/types";
import { blockLabels } from "@/features/content-management/lib/blockFactory";

import { PhoneMockup } from "../../shared/PhoneMockup/PhoneMockup";
import { BLOCK_EXAMPLES } from "../block-examples/blockExampleRegistry";
import { BLOCK_GUIDE } from "../model/blockGuide";
import * as styles from "./BlockGuideCard.css";

/** Editor name, purpose, when to use / avoid, then one student-side example per variant. */
export function BlockGuideCard({ type }: { type: ContentBlockType }) {
  const entry = BLOCK_GUIDE[type];
  return (
    <article className={styles.card}>
      <h3 className={styles.name}>{blockLabels[type]}</h3>
      <p className={styles.purpose}>{entry.purpose}</p>
      <ul className={styles.rules}>
        <li className={styles.rule}>
          <span className={styles.ruleDo}>✓</span>
          {entry.use}
        </li>
        <li className={styles.rule}>
          <span className={styles.ruleDont}>✕</span>
          {entry.avoid}
        </li>
      </ul>
      {BLOCK_EXAMPLES[type].map(({ caption, Component, interactive }, index) => (
        <div key={caption ?? index} className={styles.example}>
          {caption ? <span className={styles.caption}>{caption}</span> : null}
          <PhoneMockup interactive={interactive}>
            <Component />
          </PhoneMockup>
        </div>
      ))}
    </article>
  );
}
