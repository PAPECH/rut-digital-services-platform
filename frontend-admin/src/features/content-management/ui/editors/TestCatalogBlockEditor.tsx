import type {
  BlockEditorProps,
  TestCatalogBlock,
} from "@/entities/content/model/types";
import { SystemCollectionBlockFields } from "./SystemCollectionBlockFields";

export function TestCatalogBlockEditor({
  block,
  onChange,
}: BlockEditorProps<TestCatalogBlock>) {
  return (
    <SystemCollectionBlockFields
      title={block.title}
      description="Показывает активные опубликованные тесты текущего бота."
      onTitleChange={(title) => onChange({ ...block, title })}
    />
  );
}
