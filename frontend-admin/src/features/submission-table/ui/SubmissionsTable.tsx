import type { Submission, SubmissionStatus } from "@/api/types";
import type { FormField } from "@/entities/form/model/types";
import type { SubmissionProfileColumn } from "@/features/submission-profile/model/submissionProfile";
import {
  formatSubmissionProfileValue,
  submissionFullName,
  submissionProfileValue,
} from "@/features/submission-profile/model/submissionProfile";
import { Avatar } from "@/components/Avatar";
import { StatusTag } from "@/components/StatusTag";
import { actionLabel, formatDateTime } from "@/lib/status";
import { SubmissionTableFieldValue } from "./SubmissionTableFieldValue";
import * as styles from "./SubmissionsTable.css";

const NEXT_STATUSES: Record<SubmissionStatus, SubmissionStatus[]> = {
  new: ["in_work", "rejected"],
  in_work: ["done", "rejected"],
  rejected: [],
  done: [],
};

/** Results table for `SubmissionsPage.tsx`, rendering the same shape in both view modes (Task
 * 081) -- only the length of `tableFields` differs between "compact" (first 4 active fields) and
 * "wide" (every active field). Mirrors `form_tests`' `AttemptsWideTable` bounded-scroll treatment
 * so a form with many fields scrolls within its own box instead of growing the page. */
export function SubmissionsTable({
  profileColumns,
  tableFields,
  submissions,
  loading,
  onOpenUser,
  onOpenCard,
  onChangeStatus,
}: {
  profileColumns: SubmissionProfileColumn[];
  tableFields: FormField[];
  submissions: Submission[];
  loading: boolean;
  onOpenUser: (userId: number) => void;
  onOpenCard: (submission: Submission) => void;
  onChangeStatus: (submission: Submission, status: SubmissionStatus) => void;
}) {
  const columnCount = 4 + profileColumns.length + tableFields.length;

  return (
    <div className={styles.tableWrap}>
      <table className={`tbl ${styles.table}`}>
        <thead>
          <tr>
            <th className={styles.stickyHeadCell}>№</th>
            {profileColumns.map((column) => (
              <th className={styles.stickyHeadCell} key={column.key}>
                {column.label}
              </th>
            ))}
            {tableFields.map((f) => (
              <th className={styles.stickyHeadCell} key={f.key}>
                {f.label}
              </th>
            ))}
            <th className={styles.stickyHeadCell}>Статус</th>
            <th className={styles.stickyHeadCell}>Создана</th>
            <th className={styles.stickyHeadCell}>Действия</th>
          </tr>
        </thead>
        <tbody>
          {submissions.map((s) => (
            <tr key={s.id}>
              <td className="mono">{s.id}</td>
              {profileColumns.map((column) => (
                <td key={column.key}>
                  {column.key === "full_name" ? (
                    <button
                      type="button"
                      className="submission-user-link"
                      disabled={!s.submitter}
                      onClick={() => {
                        if (s.submitter) onOpenUser(s.submitter.id);
                      }}
                    >
                      <SubmitterCell sub={s} />
                    </button>
                  ) : (
                    formatSubmissionProfileValue(submissionProfileValue(s, column.key), column.type)
                  )}
                </td>
              ))}
              {tableFields.map((f) => (
                <td key={f.key}>
                  <SubmissionTableFieldValue field={f} value={s.values?.[f.key]} onOpen={() => onOpenCard(s)} />
                </td>
              ))}
              <td>
                <StatusTag status={s.status} />
              </td>
              <td className="num">{formatDateTime(s.created_at)}</td>
              <td>
                <div style={{ display: "flex", gap: 6, justifyContent: "flex-end" }}>
                  <button className="btn btn-primary btn-sm" type="button" onClick={() => onOpenCard(s)}>
                    Открыть
                  </button>
                  {NEXT_STATUSES[s.status].map((next) => (
                    <button
                      key={next}
                      className={`btn btn-sm ${next === "rejected" ? "btn-danger" : "btn-secondary"}`}
                      onClick={() => onChangeStatus(s, next)}
                    >
                      {actionLabel(next)}
                    </button>
                  ))}
                </div>
              </td>
            </tr>
          ))}
          {!loading && submissions.length === 0 && (
            <tr>
              <td colSpan={columnCount} className={styles.emptyRow}>
                Заявок нет
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function SubmitterCell({ sub }: { sub: Submission }) {
  const s = sub.submitter;
  const name = submissionFullName(sub);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <Avatar size="sm" user={{ photo_url: s?.photo_url, fullName: name }} />
      <div>
        <div style={{ fontWeight: 600 }}>{name}</div>
        {s?.username && <div style={{ fontSize: 11.5, color: "var(--ink-400)" }}>@{s.username}</div>}
      </div>
    </div>
  );
}
