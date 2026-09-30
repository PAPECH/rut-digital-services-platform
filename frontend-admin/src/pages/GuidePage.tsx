import { useSearchParams } from "react-router-dom";

import { ContentGuideTab } from "@/features/admin-guide/content-guide/ContentGuideTab";
import { FormGuideTab } from "@/features/admin-guide/form-guide/FormGuideTab";
import { GuideInteractionHint } from "@/features/admin-guide/shared/GuideInteractionHint/GuideInteractionHint";
import {
  GUIDE_TABS,
  parseGuideTab,
  type GuideTabKey,
} from "@/features/admin-guide/model/guideTabs";
import * as styles from "./GuidePage.css";

const TAB_CONTENT: Record<GuideTabKey, () => JSX.Element> = {
  content: ContentGuideTab,
  forms: FormGuideTab,
};

/** «Инструкции» (Task 087): static how-to guide, one tab per admin section. */
export function GuidePage() {
  const [params, setParams] = useSearchParams();
  const active = parseGuideTab(params.get("tab"));
  const Tab = TAB_CONTENT[active];

  return (
    <div className="page">
      <div className={styles.head}>
        <h1 className="page-title">Инструкции</h1>
        <p className={styles.subtitle}>
          Как наполнять бота: что добавлять, как это увидит пользователь и как оформлять.
        </p>
        <div className={styles.tabs} role="tablist" aria-label="Раздел инструкции">
          {GUIDE_TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={tab.key === active}
              className={tab.key === active ? styles.tabActive : styles.tab}
              onClick={() => {
                setParams({ tab: tab.key });
                window.scrollTo({ top: 0 });
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      <GuideInteractionHint />
      <Tab />
    </div>
  );
}
