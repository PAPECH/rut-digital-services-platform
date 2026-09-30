import type {
  BlockRendererProps,
  TestAttemptHistoryBlock,
} from "@/entities/content/model/types";
import { useIsPreviewMode } from "@/features/content/model/PreviewModeContext";
import { TestAttemptHistory } from "@/features/form-tests/ui/TestAttemptHistory";

export function TestAttemptHistoryBlockRenderer({
  block,
}: BlockRendererProps<TestAttemptHistoryBlock>) {
  if (useIsPreviewMode()) {
    return (
      <section className="embedded-system-block submission-history-block">
        {block.title ? <h3 className="section-label">{block.title}</h3> : null}
        <div className="card embedded-system-state">
          Результаты тестов недоступны в предпросмотре — здесь нет реального пользователя.
        </div>
      </section>
    );
  }
  return <TestAttemptHistory title={block.title} />;
}
