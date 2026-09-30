import { useState } from "react";

import { getCurrentAdminId } from "@/api/client";
import { UserCardPanel } from "@/components/UserCardPanel";
import type {
  AdminAttemptSummary,
  AdminTestDetail,
  TestAttemptStatus,
} from "@/entities/form-test/model/types";
import { answerableElements, numberElements } from "@/features/form-test-management/lib/answerValue";
import { useAttemptsDisplayPrefs } from "@/features/form-test-management/model/useAttemptsDisplayPrefs";
import { AttemptsWideTable } from "./attempts/AttemptsWideTable";
import { ExportAttemptsButton } from "./ExportAttemptsButton";
import { TestAttemptDrawer } from "./TestAttemptDrawer";
import { TestAttemptsTable } from "./TestAttemptsTable";
import * as styles from "./TestResultsSection.css";

const STATUS_TABS: Array<{ value: TestAttemptStatus | "all"; label: string }> = [
  { value: "all", label: "Все" },
  { value: "in_progress", label: "В процессе" },
  { value: "completed", label: "Завершённые" },
];

/** The results-viewing/export surface (Task 077), a tab of its own separate from the test
 * constructor. Owns the view-mode ("table" wide vs "drawer" compact+detail) and value-mode
 * ("text" vs "score") toggles shared by both the wide table and the attempt drawer, plus the
 * export button and the clickable submitter's `UserCardPanel`. */
export function TestResultsSection({
  testId,
  detail,
  attempts,
  statusFilter,
  onStatusFilterChange,
  loading,
}: {
  testId: number;
  detail: AdminTestDetail;
  attempts: AdminAttemptSummary[];
  statusFilter: TestAttemptStatus | "all";
  onStatusFilterChange: (status: TestAttemptStatus | "all") => void;
  loading: boolean;
}) {
  const { viewMode, setViewMode, valueMode, setValueMode } = useAttemptsDisplayPrefs();
  const [openAttemptId, setOpenAttemptId] = useState<number | null>(null);
  const [openUserId, setOpenUserId] = useState<number | null>(null);
  const currentAdminId = getCurrentAdminId();

  const elements = answerableElements(detail.test_schema.elements);
  const numberByKey = numberElements(detail.test_schema.elements);
  const resultScales = detail.test_schema.result_scales;

  return (
    <div className={`card ${styles.card}`}>
      <div className="card-head">
        <h3 className="card-title">Результаты</h3>
        <div className="pill-tabs" role="group" aria-label="Вид результатов">
          <button className={viewMode === "table" ? "active" : ""} onClick={() => setViewMode("table")}>
            Таблица
          </button>
          <button className={viewMode === "drawer" ? "active" : ""} onClick={() => setViewMode("drawer")}>
            Список
          </button>
        </div>
      </div>
      <div className="card-body">
        <div className={styles.toolbar}>
          <div className="pill-tabs">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.value}
                className={statusFilter === tab.value ? "active" : ""}
                onClick={() => onStatusFilterChange(tab.value)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className={styles.toolbarGroup}>
            <div className="pill-tabs" role="group" aria-label="Отображение ответов">
              <button className={valueMode === "text" ? "active" : ""} onClick={() => setValueMode("text")}>
                Текст
              </button>
              <button className={valueMode === "score" ? "active" : ""} onClick={() => setValueMode("score")}>
                Баллы
              </button>
            </div>
            <ExportAttemptsButton testId={testId} valueMode={valueMode} />
          </div>
        </div>

        {viewMode === "table" ? (
          <AttemptsWideTable
            attempts={attempts}
            elements={elements}
            numberByKey={numberByKey}
            resultScales={resultScales}
            valueMode={valueMode}
            loading={loading}
            onOpenAttempt={setOpenAttemptId}
            onOpenUser={setOpenUserId}
          />
        ) : (
          <TestAttemptsTable
            attempts={attempts}
            loading={loading}
            onOpenAttempt={setOpenAttemptId}
            onOpenUser={setOpenUserId}
          />
        )}
      </div>

      {openAttemptId != null && (
        <TestAttemptDrawer
          testId={testId}
          attemptId={openAttemptId}
          elements={elements}
          numberByKey={numberByKey}
          resultScales={resultScales}
          valueMode={valueMode}
          onClose={() => setOpenAttemptId(null)}
          onOpenUser={setOpenUserId}
        />
      )}

      {openUserId != null && (
        <UserCardPanel
          userId={openUserId}
          currentAdminId={currentAdminId}
          onClose={() => setOpenUserId(null)}
        />
      )}
    </div>
  );
}
