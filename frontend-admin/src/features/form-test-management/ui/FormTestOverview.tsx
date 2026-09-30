import type {
  AdminTestDetail,
  AdminTestSummary,
} from "@/entities/form-test/model/types";
import { answerableElements } from "@/features/form-test-management/lib/answerValue";
import { FormTestStatusToggle } from "./FormTestStatusToggle";
import * as styles from "./FormTestOverview.css";

export function FormTestOverview({
  detail,
  busy,
  onToggle,
}: {
  detail: AdminTestDetail | null;
  busy: boolean;
  onToggle: (
    payload: Partial<Pick<AdminTestSummary, "is_active" | "is_archived">>,
  ) => void;
}) {
  if (!detail) {
    return (
      <div className="card">
        <div className={styles.empty}>Выберите тест слева</div>
      </div>
    );
  }

  const questionCount = answerableElements(detail.test_schema.elements).length;
  const filterByScale = new Map(
    detail.test_schema.filters.map((filter) => [filter.result_scale_key, filter]),
  );

  return (
    <div className="card">
      <div className="card-body">
        <div className={styles.header}>
          <div>
            <div className={styles.title}>{detail.name}</div>
            <div className={styles.subtitle}>
              /{detail.slug} · опубликованная версия{" "}
              {detail.published_version_id ?? "—"}
              {detail.consent_enabled && ` · согласие: «${detail.consent_document_title ?? "—"}»`}
            </div>
          </div>
          <FormTestStatusToggle test={detail} busy={busy} onToggle={onToggle} />
        </div>

        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <div className={styles.statValue}>{questionCount}</div>
            <div className={styles.statLabel}>вопросов</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>
              {detail.test_schema.result_scales.length}
            </div>
            <div className={styles.statLabel}>рассчитываемых шкал</div>
          </div>
          <div className={styles.statCard}>
            <div className={styles.statValue}>
              {detail.test_schema.filters.length}
            </div>
            <div className={styles.statLabel}>шкал с интерпретацией</div>
          </div>
        </div>

        <div className={styles.scaleList}>
          {detail.test_schema.result_scales.map((scale) => {
            const filter = filterByScale.get(scale.key);
            return (
              <div key={scale.key} className={styles.scaleRow}>
                <span className={styles.scaleName}>{scale.label}</span>
                <span className={styles.scaleMeta}>
                  {scale.terms.length} терм(ов), {scale.aggregation === "sum" ? "сумма" : "среднее"}
                  {filter ? `, ${filter.rules.length} диапазона(ов)` : ", без интерпретации"}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
