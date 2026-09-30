import type {
  BlockRendererProps,
  FaqListBlock,
} from "@/entities/content/model/types";
import { FaqCollection } from "@/features/faq/ui/FaqCollection";

export function FaqListBlockRenderer({
  block,
  content,
}: BlockRendererProps<FaqListBlock>) {
  return (
    <FaqCollection
      title={block.title}
      analyticsContext={{
        categoryId: content.id,
        // Non-null: a faq_list block only ever renders inside a real published page, never a
        // capability shortcut (which has no blocks at all).
        contentVersionId: content.version_id as number,
        blockId: block.id,
      }}
    />
  );
}
