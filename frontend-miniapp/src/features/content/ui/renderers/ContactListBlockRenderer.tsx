import type {
  BlockRendererProps,
  ContactListBlock,
} from "@/entities/content/model/types";
import { trackAnalyticsEventInBackground } from "@/features/analytics/api/analyticsApi";
import { openLink } from "@/max/bridge";

export function ContactListBlockRenderer({
  block,
  content,
}: BlockRendererProps<ContactListBlock>) {
  const open = (href: string) => {
    trackAnalyticsEventInBackground({
      action_type: "content_block_interaction",
      interaction_kind: "contact_open",
      source_surface: "category",
      category_id: content.id,
      content_version_id: content.version_id,
      block_id: block.id,
    });
    openLink(href);
  };
  return (
    <dl className="cms-contacts">
      {block.items.map((item, index) => (
        <div key={`${item.label}-${index}`}>
          <dt>{item.label}</dt>
          <dd>
            {item.href ? (
              <button type="button" onClick={() => open(item.href!)}>
                {item.value}
              </button>
            ) : (
              item.value
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
