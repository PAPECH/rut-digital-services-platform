import { useState } from "react";

import type { PublishedTestDetail, TestAttempt } from "@/entities/form-test/model/types";
import { useI18n } from "@/i18n";
import * as styles from "./TestResultScreen.css";

// Shown both right after completing a test and whenever a student reopens one they already
// completed -- the mini-app never had a dedicated result screen before Task 075, only a dead-end
// "already completed" message with nothing on it.
export function TestResultScreen({
  test,
  attempt,
  onRetake,
  onBack,
}: {
  test: PublishedTestDetail;
  attempt: TestAttempt;
  onRetake?: () => Promise<void>;
  onBack: () => void;
}) {
  const { t } = useI18n();
  const [retaking, setRetaking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scoreEntries = attempt.computed_results ? Object.entries(attempt.computed_results) : [];

  const handleRetake = async () => {
    if (!onRetake) return;
    setError(null);
    setRetaking(true);
    try {
      await onRetake();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("tests:result:retake_error"));
    } finally {
      setRetaking(false);
    }
  };

  return (
    <div className="screen test-page-screen">
      <div className={styles.wrap}>
        <div className={styles.title}>{t("tests:completed:title")}</div>

        {attempt.rendered_result_text ? (
          <p className={styles.resultText}>{attempt.rendered_result_text}</p>
        ) : (
          <p className={styles.message}>{t("tests:completed:message")}</p>
        )}

        {scoreEntries.length > 0 ? (
          <div className={styles.scores}>
            <span className={styles.scoresLabel}>{t("tests:result:scores_title")}</span>
            {scoreEntries.map(([key, entry]) => (
              <div key={key} className={styles.scoreRow}>
                <span>{test.result_scale_labels?.[key] ?? key}</span>
                <span className={styles.scoreValue}>{entry.value}</span>
              </div>
            ))}
          </div>
        ) : null}

        {error ? <div className={styles.errorBanner}>{error}</div> : null}

        <div className={styles.actions}>
          {onRetake ? (
            <button
              type="button"
              className="btn btn-secondary"
              disabled={retaking}
              onClick={() => void handleRetake()}
            >
              {retaking ? t("tests:result:retaking") : t("tests:result:retake_button")}
            </button>
          ) : null}
          <button type="button" className="btn btn-primary" onClick={onBack}>
            {t("tests:completed:back")}
          </button>
        </div>
      </div>
    </div>
  );
}
