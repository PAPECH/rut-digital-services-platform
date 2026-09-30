import type { ContentBlockType } from "@/entities/content/model/types";

import { BLOCK_GROUPS, BLOCK_GUIDE } from "../model/blockGuide";
import { BlockGuideCard } from "../BlockGuideCard/BlockGuideCard";
import * as styles from "./BlockCatalog.css";

const BLOCK_TYPES = Object.keys(BLOCK_GUIDE) as ContentBlockType[];

export function BlockCatalog() {
  return (
    <>
      {BLOCK_GROUPS.map((group) => (
        <div key={group.key} className={styles.group}>
          <h3 className={styles.groupTitle}>{group.title}</h3>
          <div className={styles.cards}>
            {BLOCK_TYPES.filter((type) => BLOCK_GUIDE[type].group === group.key).map((type) => (
              <BlockGuideCard key={type} type={type} />
            ))}
          </div>
        </div>
      ))}
    </>
  );
}
