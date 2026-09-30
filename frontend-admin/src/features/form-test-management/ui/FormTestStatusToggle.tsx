import type { AdminTestSummary } from "@/entities/form-test/model/types";
import * as styles from "./FormTestStatusToggle.css";

export function FormTestStatusToggle({
  test,
  busy,
  onToggle,
}: {
  test: AdminTestSummary;
  busy: boolean;
  onToggle: (
    payload: Partial<Pick<AdminTestSummary, "is_active" | "is_archived">>,
  ) => void;
}) {
  return (
    <div className={styles.row}>
      <button
        type="button"
        className={`btn btn-sm ${test.is_active ? "btn-secondary" : "btn-primary"}`}
        disabled={busy || test.is_archived}
        onClick={() => onToggle({ is_active: !test.is_active })}
      >
        {test.is_active ? "Скрыть" : "Показать"}
      </button>
      <button
        type="button"
        className={`btn btn-sm ${test.is_archived ? "btn-secondary" : "btn-danger"}`}
        disabled={busy}
        onClick={() => onToggle({ is_archived: !test.is_archived })}
      >
        {test.is_archived ? "Восстановить" : "Архивировать"}
      </button>
    </div>
  );
}
