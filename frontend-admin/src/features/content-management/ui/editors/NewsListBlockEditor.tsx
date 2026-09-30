import type {
  BlockEditorProps,
  NewsListBlock,
} from "@/entities/content/model/types";
import { SystemCollectionBlockFields } from "./SystemCollectionBlockFields";

export function NewsListBlockEditor({
  block,
  onChange,
}: BlockEditorProps<NewsListBlock>) {
  return (
    <SystemCollectionBlockFields
      title={block.title}
      description="Показывает активные новости текущего бота, от новых к старым."
      onTitleChange={(title) => onChange({ ...block, title })}
    />
  );
}
