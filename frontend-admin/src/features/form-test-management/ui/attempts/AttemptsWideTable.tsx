import { Fragment } from "react";
import type {
  AdminAttemptSummary,
  FormTestElement,
  ResultScale,
} from "@/entities/form-test/model/types";
import { answerDisplayValue, type AttemptValueMode } from "@/features/form-test-management/lib/answerValue";
import { formatDateTime } from "@/lib/status";
import { AttemptSubmitterCell } from "./AttemptSubmitterCell";
import * as styles from "./AttemptsWideTable.css";

const STATUS_LABEL: Record<AdminAttemptSummary["status"], string> = {
  in_progress: "В процессе",
  completed: "Завершена",
};

/** One row per attempt, one column per question followed by one column pair per result scale --
 * the "table" view mode (Task 077), mirroring how `SubmissionsPage.tsx` renders form fields as
 * columns. Question columns always come before scale columns. */
export function AttemptsWideTable({
  attempts,
  elements,
  numberByKey,
  resultScales,
  valueMode,
  loading,
  onOpenAttempt,
  onOpenUser,
}: {
  attempts: AdminAttemptSummary[];
  elements: FormTestElement[];
  numberByKey: Map<string, number>;
  resultScales: ResultScale[];
  valueMode: AttemptValueMode;
  loading: boolean;
  onOpenAttempt: (attemptId: number) => void;
  onOpenUser: (userId: number) => void;
}) {
  const columnCount = 6 + elements.length + resultScales.length * 2;

  return (
    <div className={styles.tableWrap}>
      <table className={`tbl ${styles.table}`}>
        <thead>
          <tr>
            <th className={styles.stickyHeadCell}>№</th>
            <th className={styles.stickyHeadCell}>Пользователь</th>
            <th className={styles.stickyHeadCell}>Статус</th>
            <th className={styles.stickyHeadCell}>Начата</th>
            <th className={styles.stickyHeadCell}>Завершена</th>
            {elements.map((element) => (
              <th className={styles.stickyHeadCell} key={element.key}>
                {numberByKey.get(element.key)}) {element.label}
              </th>
            ))}
            {resultScales.map((scale) => (
              <th className={styles.stickyHeadCell} key={scale.key} colSpan={2}>
                {scale.label}
              </th>
            ))}
            <th className={styles.stickyHeadCell}>Действия</th>
          </tr>
        </thead>
        <tbody>
          {attempts.map((attempt) => (
            <tr key={attempt.id}>
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
              {elements.map((element) => (
                <td key={element.key}>{answerDisplayValue(element, attempt.answers, valueMode)}</td>
              ))}
              {resultScales.map((scale) => {
                const entry = attempt.computed_results?.[scale.key];
                return (
                  <Fragment key={scale.key}>
                    <td className={styles.scaleValueCell}>{entry ? entry.value : "—"}</td>
                    <td className={styles.scaleLabelCell}>{entry?.filter?.label ?? "—"}</td>
                  </Fragment>
                );
              })}
              <td>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => onOpenAttempt(attempt.id)}>
                  Открыть
                </button>
              </td>
            </tr>
          ))}
          {!loading && attempts.length === 0 && (
            <tr>
              <td colSpan={columnCount} className={styles.emptyRow}>
                Попыток нет
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
