import type {
  BlockRendererProps,
  LinkBlock,
} from "@/entities/content/model/types";
import { trackAnalyticsEventInBackground } from "@/features/analytics/api/analyticsApi";
import { openLink } from "@/max/bridge";

export function LinkBlockRenderer({ block, content }: BlockRendererProps<LinkBlock>) {
  const open = () => {
    trackAnalyticsEventInBackground({
      action_type: "content_block_interaction",
      interaction_kind: "link_open",
      source_surface: "category",
      category_id: content.id,
      content_version_id: content.version_id,
      block_id: block.id,
    });
    openLink(block.href);
  };
  return (
    <button
      type="button"
      className={`cms-link cms-link--${block.style}`}
      onClick={open}
    >
      <span>{block.title}</span>
      <span aria-hidden="true">→</span>
    </button>
  );
}
