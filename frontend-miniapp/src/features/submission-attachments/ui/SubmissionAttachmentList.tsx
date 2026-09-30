import type { SubmissionAttachment } from "@/api/types";
import { SubmissionAttachmentItem } from "@/features/submission-attachments/ui/SubmissionAttachmentItem";

export function SubmissionAttachmentList({
  items,
}: {
  items: SubmissionAttachment[];
}) {
  return (
    <div className="history-attachments">
      {items.map((item) => (
        <SubmissionAttachmentItem item={item} key={item.id} />
      ))}
    </div>
  );
}
