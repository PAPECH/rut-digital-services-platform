import type {
  BlockRendererProps,
  CategoryGridBlock,
} from "@/entities/content/model/types";
import { ContentCategoryGrid } from "@/features/content/ui/ContentCategoryGrid";

export function CategoryGridBlockRenderer({
  block,
}: BlockRendererProps<CategoryGridBlock>) {
  return (
    <ContentCategoryGrid
      parentId={block.parent_id}
      {...(block.title ? { title: block.title } : {})}
    />
  );
}
