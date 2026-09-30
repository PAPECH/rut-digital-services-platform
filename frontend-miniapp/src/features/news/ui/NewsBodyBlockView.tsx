import { useState } from "react";

import type { AttachmentUrlEntry, NewsBodyBlock } from "@/entities/content/model/types";
import { RichTextView } from "@/features/content/ui/RichTextView";
import { ContentAttachmentPreview } from "@/features/content/ui/ContentAttachmentPreview";
import { downloadFile, openLink } from "@/max/bridge";

// Renders the same content-shaping block types a category page uses
// (heading/paragraph/callout/contact_list/link/file_list) inside a news article body. Unlike
// `BlockRendererRegistry` in `features/content`, this does not require a `PublishedContent`
// context -- a news item is not a category page, and attributing its block interactions to a
// fake category/version id would corrupt `content_block_interaction` analytics, so link/contact/
// file taps here simply navigate without emitting that event.
export function NewsBodyBlockView({
  block,
  attachmentUrls,
}: {
  block: NewsBodyBlock;
  attachmentUrls: Record<number, AttachmentUrlEntry>;
}) {
  switch (block.type) {
    case "heading": {
      const level = block.level >= 1 && block.level <= 6 ? block.level : 2;
      const Tag = `h${level}` as keyof JSX.IntrinsicElements;
      return <Tag className={`cms-heading cms-heading--${level}`}>{block.text}</Tag>;
    }
    case "paragraph":
      return <RichTextView value={block.text} className="cms-paragraph" />;
    case "callout":
      return (
        <aside className={`cms-callout cms-callout--${block.tone}`}>
          {block.title ? <strong>{block.title}</strong> : null}
          <RichTextView value={block.text} />
        </aside>
      );
    case "contact_list":
      return (
        <dl className="cms-contacts">
          {block.items.map((item, index) => (
            <div key={`${item.label}-${index}`}>
              <dt>{item.label}</dt>
              <dd>
                {item.href ? (
                  <button type="button" onClick={() => openLink(item.href!)}>
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
    case "link":
      return (
        <button
          type="button"
          className={`cms-link cms-link--${block.style}`}
          onClick={() => openLink(block.href)}
        >
          <span>{block.title}</span>
          <span aria-hidden="true">→</span>
        </button>
      );
    case "file_list":
      return <NewsFileList block={block} attachmentUrls={attachmentUrls} />;
    default:
      return null;
  }
}

function NewsFileList({
  block,
  attachmentUrls,
}: {
  block: Extract<NewsBodyBlock, { type: "file_list" }>;
  attachmentUrls: Record<number, AttachmentUrlEntry>;
}) {
  const [previewItem, setPreviewItem] = useState<{ name: string; url: string } | null>(null);

  return (
    <div className="cms-files">
      {block.items.map((item) => {
        const entry = attachmentUrls[item.attachment_id];
        const url = entry ? window.location.origin + entry.url : null;
        const isImage = Boolean(entry?.mime.startsWith("image/"));
        const key = `${item.attachment_id}-${item.title}`;

        if (item.display_mode === "inline_image" && isImage && url) {
          return <img key={key} className="cms-files__inline-image" src={url} alt={item.title} />;
        }

        return (
          <div className="cms-files__item" key={key}>
            {isImage && url ? (
              <button
                type="button"
                className="cms-files__thumb"
                aria-label={`Предпросмотр ${item.title}`}
                onClick={() => setPreviewItem({ name: item.title, url })}
              >
                <img src={url} alt="" />
              </button>
            ) : (
              <span className="cms-files__icon" aria-hidden="true">
                ↓
              </span>
            )}
            <button
              type="button"
              className="cms-files__download"
              disabled={!url}
              onClick={() => url && downloadFile(url, item.title)}
            >
              <span>
                <strong>{item.title}</strong>
                {item.description ? <small>{item.description}</small> : null}
              </span>
            </button>
          </div>
        );
      })}
      {previewItem ? (
        <ContentAttachmentPreview
          name={previewItem.name}
          url={previewItem.url}
          onClose={() => setPreviewItem(null)}
        />
      ) : null}
    </div>
  );
}
