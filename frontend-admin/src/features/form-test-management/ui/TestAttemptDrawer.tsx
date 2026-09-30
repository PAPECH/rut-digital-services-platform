import { useEffect, useState } from "react";

import type { AdminAttemptDetail, FormTestElement, ResultScale } from "@/entities/form-test/model/types";
import { formTestApi } from "@/features/form-test-management/api/formTestApi";
import { answerDisplayValue, type AttemptValueMode } from "@/features/form-test-management/lib/answerValue";
import { formatDateTime } from "@/lib/status";
import { AttemptSubmitterCell } from "./attempts/AttemptSubmitterCell";
import * as styles from "./TestAttemptDrawer.css";

export function TestAttemptDrawer({
  testId,
  attemptId,
  elements,
  numberByKey,
  resultScales,
  valueMode,
  onClose,
  onOpenUser,
}: {
  testId: number;
  attemptId: number;
  elements: FormTestElement[];
  numberByKey: Map<string, number>;
  resultScales: ResultScale[];
  valueMode: AttemptValueMode;
  onClose: () => void;
  onOpenUser: (userId: number) => void;
}) {
  const [detail, setDetail] = useState<AdminAttemptDetail | null>(null);

  useEffect(() => {
    let cancelled = false;
    setDetail(null);
    void formTestApi.attemptDetail(testId, attemptId).then((result) => {
      if (!cancelled) setDetail(result);
    });
    return () => {
      cancelled = true;
    };
  }, [testId, attemptId]);

  const labelByScaleKey = new Map(resultScales.map((scale) => [scale.key, scale.label]));

  return (
    <div className={styles.overlay}>
      <div className={styles.backdrop} onClick={onClose} />
      <div className={styles.panel}>
        <div className={styles.head}>
          <div>
            <div className={styles.headTitle}>Попытка #{attemptId}</div>
            {detail && (
              <div className={styles.headSubtitle}>
                <AttemptSubmitterCell userId={detail.user_id} submitter={detail.submitter} onOpen={onOpenUser} />
              </div>
            )}
          </div>
          <button type="button" className="btn btn-ghost btn-icon" onClick={onClose}>
            ×
          </button>
        </div>

        <div className={styles.body}>
          {!detail ? (
            <div className={styles.loadingState}>Загрузка…</div>
          ) : (
            <>
              <div className={styles.answerRow}>
                <span className={styles.answerLabel}>Начата</span>
                <span>{formatDateTime(detail.started_at)}</span>
              </div>
              <div className={styles.answerRow}>
                <span className={styles.answerLabel}>Завершена</span>
                <span>{formatDateTime(detail.completed_at)}</span>
              </div>
              <div className={styles.answerRow}>
                <span className={styles.answerLabel}>Согласие на участие</span>
                <span>
                  {detail.consent_accepted
                    ? `получено ${formatDateTime(detail.consent_accepted_at)}`
                    : "не требовалось / не дано"}
                </span>
              </div>

              {elements.length > 0 && (
                <>
                  <h4 className={styles.sectionTitle}>Ответы на вопросы</h4>
                  {elements.map((element) => (
                    <div key={element.key} className={styles.answerRow}>
                      <span className={styles.answerLabel}>
                        {numberByKey.get(element.key)}) {element.label}
                      </span>
                      <span>{answerDisplayValue(element, detail.answers, valueMode)}</span>
                    </div>
                  ))}
                </>
              )}

              <h4 className={styles.sectionTitle}>Результаты по шкалам</h4>
              {detail.computed_results &&
                Object.entries(detail.computed_results).map(([scaleKey, entry]) => (
                  <div key={scaleKey} className={styles.scaleRow}>
                    <span className={styles.scaleLabel}>
                      {labelByScaleKey.get(scaleKey) ?? scaleKey}
                    </span>
                    <span className={styles.scaleValue}>
                      <span>
                        {entry.value}
                        {entry.filter?.is_flagged && (
                          <span className={`tag danger ${styles.flaggedTag}`}>риск</span>
                        )}
                      </span>
                      {entry.filter && (
                        <span className={styles.scaleValueMeta}>{entry.filter.label}</span>
                      )}
                    </span>
                  </div>
                ))}

              {detail.rendered_result_text && (
                <>
                  <h4 className={styles.sectionTitle}>Отправленный текст результата</h4>
                  <div className={styles.resultText}>{detail.rendered_result_text}</div>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
