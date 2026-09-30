import type {
  BlockRendererProps,
  FormCatalogBlock,
} from "@/entities/content/model/types";
import { FormCatalog } from "@/features/forms/ui/FormCatalog";

export function FormCatalogBlockRenderer({
  block,
  content,
}: BlockRendererProps<FormCatalogBlock>) {
  return (
    <FormCatalog
      title={block.title}
      analyticsContext={{
        categoryId: content.id,
        // Non-null: a form_catalog block only ever renders inside a real published page, never
        // a capability shortcut (which has no blocks at all).
        contentVersionId: content.version_id as number,
        blockId: block.id,
      }}
    />
  );
}
