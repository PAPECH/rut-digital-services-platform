import type {
  BlockEditorProps,
  TestAttemptHistoryBlock,
} from "@/entities/content/model/types";
import { SystemCollectionBlockFields } from "./SystemCollectionBlockFields";

export function TestAttemptHistoryBlockEditor({
  block,
  onChange,
}: BlockEditorProps<TestAttemptHistoryBlock>) {
  return (
    <SystemCollectionBlockFields
      title={block.title}
      description="Показывает только попытки прохождения тестов авторизованного пользователя в текущем боте."
      onTitleChange={(title) => onChange({ ...block, title })}
    />
  );
}
