import type {
  BlockRendererProps,
  ParagraphBlock,
} from "@/entities/content/model/types";
import { RichTextView } from "@/features/content/ui/RichTextView";

export function ParagraphBlockRenderer({
  block,
}: BlockRendererProps<ParagraphBlock>) {
  return <RichTextView value={block.text} className="cms-paragraph" />;
}
