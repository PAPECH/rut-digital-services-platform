import type {
  BlockRendererProps,
  LinkBlock,
} from "@/entities/content/model/types";
import { trackAnalyticsEventInBackground } from "@/features/analytics/api/analyticsApi";
import { getApiBotSlug } from "@/lib/botSlug";
import { openLink } from "@/max/bridge";

import "./LinkBlockRenderer.css";

const KRUTYA_BOT_SLUG = "krutya_bot";
const KRUTYA_HOME_SLUG = "system-home-screen";

function isUnavailableKrutyaService(block: LinkBlock, contentSlug: string): boolean {
  return (
    getApiBotSlug() === KRUTYA_BOT_SLUG &&
    contentSlug === KRUTYA_HOME_SLUG &&
    block.title.startsWith("Чат-бот ") &&
    !block.title.includes("Ректор")
  );
}

export function LinkBlockRenderer({ block, content }: BlockRendererProps<LinkBlock>) {
  const unavailable = isUnavailableKrutyaService(block, content.slug);

  if (unavailable) {
    return (
      <div
        className={`cms-link cms-link--${block.style} cms-link--unavailable`}
        aria-disabled="true"
      >
        <span className="cms-link__unavailable-content">
          <span>{block.title}</span>
          <span className="cms-link__unavailable-caption">
            Не подключён к конкурсному стенду
          </span>
        </span>
      </div>
    );
  }

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
