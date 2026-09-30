import type { AdminAttemptSummary } from "@/entities/form-test/model/types";
import { TestAttemptRow } from "./TestAttemptRow";
import * as styles from "./TestAttemptsTable.css";

/** The compact attempt list ("drawer" view mode, Task 077) -- opening a row shows the full
 * per-question breakdown in `TestAttemptDrawer`. Status filter, value-mode toggle, and export sit
 * one level up in `TestResultsSection`, shared with the wide-table view mode. */
export function TestAttemptsTable({
  attempts,
  loading,
  onOpenAttempt,
  onOpenUser,
}: {
  attempts: AdminAttemptSummary[];
  loading: boolean;
  onOpenAttempt: (attemptId: number) => void;
  onOpenUser: (userId: number) => void;
}) {
  return (
    <div className={styles.tableWrap}>
      <table className="tbl">
        <thead>
          <tr>
            <th className={styles.stickyHeadCell}>№</th>
            <th className={styles.stickyHeadCell}>Пользователь</th>
            <th className={styles.stickyHeadCell}>Статус</th>
            <th className={styles.stickyHeadCell}>Начата</th>
            <th className={styles.stickyHeadCell}>Завершена</th>
            <th className={styles.stickyHeadCell}>Согласие</th>
            <th className={styles.stickyHeadCell}>Действия</th>
          </tr>
        </thead>
        <tbody>
          {attempts.map((attempt) => (
            <TestAttemptRow
              key={attempt.id}
              attempt={attempt}
              onOpen={() => onOpenAttempt(attempt.id)}
              onOpenUser={onOpenUser}
            />
          ))}
          {!loading && attempts.length === 0 && (
            <tr>
              <td colSpan={7} className={styles.emptyRow}>
                Попыток нет
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
