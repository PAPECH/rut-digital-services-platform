import type { AdminAttemptSummary } from "@/entities/form-test/model/types";
import { formatDateTime } from "@/lib/status";
import { AttemptSubmitterCell } from "./attempts/AttemptSubmitterCell";

const STATUS_LABEL: Record<AdminAttemptSummary["status"], string> = {
  in_progress: "В процессе",
  completed: "Завершена",
};

export function TestAttemptRow({
  attempt,
  onOpen,
  onOpenUser,
}: {
  attempt: AdminAttemptSummary;
  onOpen: () => void;
  onOpenUser: (userId: number) => void;
}) {
  return (
    <tr>
      <td className="mono">{attempt.id}</td>
      <td>
        <AttemptSubmitterCell userId={attempt.user_id} submitter={attempt.submitter} onOpen={onOpenUser} />
      </td>
      <td>
        <span className={`tag ${attempt.status === "completed" ? "success" : "neutral"}`}>
          {STATUS_LABEL[attempt.status]}
        </span>
      </td>
      <td className="num">{formatDateTime(attempt.started_at)}</td>
      <td className="num">{formatDateTime(attempt.completed_at)}</td>
      <td>{attempt.consent_accepted ? formatDateTime(attempt.consent_accepted_at) : "—"}</td>
      <td>
        <button type="button" className="btn btn-secondary btn-sm" onClick={onOpen}>
          Открыть
        </button>
      </td>
    </tr>
  );
}
