import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import type {
  PublishedTestSummary,
  TestAttempt,
} from "@/entities/form-test/model/types";
import { formTestApi } from "@/features/form-tests/api/formTestApi";
import { useI18n } from "@/i18n";
import { formatDateTime } from "@/lib/status";

export function TestAttemptHistory({ title }: { title?: string | null }) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [attempts, setAttempts] = useState<TestAttempt[]>([]);
  const [testNames, setTestNames] = useState<Map<number, string>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    void Promise.all([formTestApi.listMyAttempts(), formTestApi.list()])
      .then(([items, tests]: [TestAttempt[], PublishedTestSummary[]]) => {
        if (!mounted) return;
        setAttempts(items);
        setTestNames(new Map(tests.map((test) => [test.id, test.name])));
      })
      .catch((loadError: unknown) => {
        if (mounted) {
          setError(
            loadError instanceof Error ? loadError.message : t("tests:history:error"),
          );
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [t]);

  return (
    <section className="embedded-system-block submission-history-block">
      {title ? <h3 className="section-label">{title}</h3> : null}
      {loading ? (
        <div className="card embedded-system-state">{t("tests:history:loading")}</div>
      ) : null}
      {error ? <div className="card form-error">{error}</div> : null}
      {!loading && !error && attempts.length === 0 ? (
        <div className="card embedded-system-state">{t("tests:history:empty")}</div>
      ) : null}
      {!loading && !error
        ? attempts.map((attempt) => (
            <button
              type="button"
              key={attempt.id}
              className="sub-card"
              onClick={() =>
                navigate(
                  attempt.status === "completed"
                    ? `/tests/${attempt.test_definition_id}?attempt=${attempt.id}`
                    : `/tests/${attempt.test_definition_id}`,
                )
              }
            >
              <span>
                <span className="name">
                  {testNames.get(attempt.test_definition_id) ??
                    `${t("word:test")} #${attempt.test_definition_id}`}
                </span>
                <span className="meta">
                  {t("word:create_at")} {formatDateTime(attempt.started_at)}
                </span>
              </span>
              <span className={`tag ${attempt.status === "completed" ? "done" : "new"}`}>
                <span className="dot" />
                {attempt.status === "completed"
                  ? t("tests:history:status_completed")
                  : t("tests:history:status_in_progress")}
              </span>
            </button>
          ))
        : null}
    </section>
  );
}
