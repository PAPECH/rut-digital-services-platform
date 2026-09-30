import type {
  BlockEditorProps,
  FaqListBlock,
} from "@/entities/content/model/types";
import { SystemCollectionBlockFields } from "./SystemCollectionBlockFields";

export function FaqListBlockEditor({
  block,
  onChange,
}: BlockEditorProps<FaqListBlock>) {
  return (
    <SystemCollectionBlockFields
      title={block.title}
      description="Показывает активные частые вопросы текущего бота в порядке, заданном на вкладке FAQ."
      onTitleChange={(title) => onChange({ ...block, title })}
    />
  );
}
