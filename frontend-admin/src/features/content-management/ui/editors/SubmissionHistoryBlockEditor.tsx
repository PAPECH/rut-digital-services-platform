import type {
  BlockEditorProps,
  SubmissionHistoryBlock,
} from "@/entities/content/model/types";
import { SystemCollectionBlockFields } from "./SystemCollectionBlockFields";

export function SubmissionHistoryBlockEditor({
  block,
  onChange,
}: BlockEditorProps<SubmissionHistoryBlock>) {
  return (
    <SystemCollectionBlockFields
      title={block.title}
      description="Показывает только заявки авторизованного пользователя в текущем боте. Просмотр статуса и файлов остаётся доступным."
      onTitleChange={(title) => onChange({ ...block, title })}
    />
  );
}
