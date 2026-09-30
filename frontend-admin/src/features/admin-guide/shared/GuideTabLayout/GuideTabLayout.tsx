import { useMemo, type ReactNode } from "react";

import type { GuideTabKey } from "../../model/guideTabs";
import { guideTab } from "../../model/guideTabs";
import type { GuideSectionLink } from "../GuideSection/GuideSection";
import { GuideToc } from "../GuideToc/GuideToc";
import { GuideUpdatedAt } from "../GuideUpdatedAt/GuideUpdatedAt";
import { PUBLISH_CYCLE_SECTION, PublishCycleDemo } from "../PublishCycleDemo/PublishCycleDemo";
import * as styles from "./GuideTabLayout.css";

/**
 * Skeleton every guide tab shares: publish-cycle banner, TOC + sections, «Актуально на» footer.
 * A new tab supplies its sections and gets the rest for free.
 */
export function GuideTabLayout({
  tab,
  sections,
  children,
}: {
  tab: GuideTabKey;
  sections: ReadonlyArray<GuideSectionLink>;
  children: ReactNode;
}) {
  const tocSections = useMemo(() => [PUBLISH_CYCLE_SECTION, ...sections], [sections]);
  return (
    <div className={styles.layout}>
      <GuideToc sections={tocSections} />
      <div className={styles.body}>
        <PublishCycleDemo />
        {children}
        <GuideUpdatedAt date={guideTab(tab).updatedAt} />
      </div>
    </div>
  );
}
