import type { SubmissionAttachment } from "@/api/types";
import { SubmissionAttachmentItem } from "@/features/submission-attachments/ui/SubmissionAttachmentItem";

export function SubmissionAttachmentList({ items }: { items: SubmissionAttachment[] }) {
  return (
    <div className="submission-attachments">
      {items.map((item) => <SubmissionAttachmentItem key={item.id} item={item} />)}
    </div>
  );
}
