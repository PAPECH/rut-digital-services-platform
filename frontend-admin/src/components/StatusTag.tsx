import type { SubmissionStatus } from "@/api/types";
import { statusClass, statusLabel } from "@/lib/status";

export function StatusTag({ status }: { status: SubmissionStatus }) {
  return (
    <span className={`tag ${statusClass(status)}`}>
      <span className="dot" />
      {statusLabel(status)}
    </span>
  );
}
