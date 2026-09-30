import type {
  BlockEditorProps,
  FormCatalogBlock,
} from "@/entities/content/model/types";
import { SystemCollectionBlockFields } from "./SystemCollectionBlockFields";

export function FormCatalogBlockEditor({
  block,
  onChange,
}: BlockEditorProps<FormCatalogBlock>) {
  return (
    <SystemCollectionBlockFields
      title={block.title}
      description="Показывает опубликованные формы текущего бота с включённым параметром «В общем каталоге»."
      onTitleChange={(title) => onChange({ ...block, title })}
    />
  );
}
