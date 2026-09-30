import type {
  BlockRendererProps,
  SubmissionHistoryBlock,
} from "@/entities/content/model/types";
import { useIsPreviewMode } from "@/features/content/model/PreviewModeContext";
import { SubmissionHistory } from "@/features/submissions/ui/SubmissionHistory";

export function SubmissionHistoryBlockRenderer({
  block,
}: BlockRendererProps<SubmissionHistoryBlock>) {
  if (useIsPreviewMode()) {
    return (
      <section className="embedded-system-block submission-history-block">
        {block.title ? <h3 className="section-label">{block.title}</h3> : null}
        <div className="card embedded-system-state">
          Список заявок недоступен в предпросмотре — здесь нет реального пользователя.
        </div>
      </section>
    );
  }
  return <SubmissionHistory title={block.title} />;
}
