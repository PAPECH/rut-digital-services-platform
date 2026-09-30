import { useState } from "react";

import type {
  BlockRendererProps,
  TabsBlock,
} from "@/entities/content/model/types";
import { trackAnalyticsEventInBackground } from "@/features/analytics/api/analyticsApi";
import { NestedBlockRendererRegistry } from "./NestedBlockRendererRegistry";

export function TabsBlockRenderer({
  block,
  content,
}: BlockRendererProps<TabsBlock>) {
  const [activeKey, setActiveKey] = useState(block.tabs[0]?.key ?? "");
  const active =
    block.tabs.find((tab) => tab.key === activeKey) ?? block.tabs[0];
  const select = (key: string) => {
    setActiveKey(key);
    trackAnalyticsEventInBackground({
      action_type: "content_tab_open",
      source_surface: "category",
      category_id: content.id,
      // Non-null: tabs only ever render inside a real published page, never a capability
      // shortcut (which has no blocks at all).
      content_version_id: content.version_id as number,
      tabs_block_id: block.id,
      tab_key: key,
    });
  };
  return (
    <section className="cms-tabs">
      <div
        className="cms-tabs__list"
        role="tablist"
        aria-label="Разделы страницы"
      >
        {block.tabs.map((tab) => (
          <button
            type="button"
            role="tab"
            aria-selected={active?.key === tab.key}
            aria-controls={`${block.id}-${tab.key}`}
            key={tab.key}
            onClick={() => select(tab.key)}
          >
            {tab.title}
          </button>
        ))}
      </div>
      {active ? (
        <div
          className="cms-tabs__panel"
          role="tabpanel"
          id={`${block.id}-${active.key}`}
        >
          {active.blocks.map((child) => (
            <NestedBlockRendererRegistry
              key={child.id}
              block={child}
              content={content}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}
