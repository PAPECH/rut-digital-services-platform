import type {
  BlockRendererProps,
  CalloutBlock,
} from "@/entities/content/model/types";
import { RichTextView } from "@/features/content/ui/RichTextView";

export function CalloutBlockRenderer({
  block,
}: BlockRendererProps<CalloutBlock>) {
  return (
    <aside className={`cms-callout cms-callout--${block.tone}`}>
      {block.title ? <strong>{block.title}</strong> : null}
      <RichTextView value={block.text} />
    </aside>
  );
}
