import { useAuth } from "@/auth/AuthProvider";
import { useI18n } from "@/i18n";
import { formatDateTime, statusClass, statusLabel } from "@/lib/status";
import { useUserSubmissions } from "../model/useUserSubmissions";
import { SubmissionSheet } from "./SubmissionSheet";

export function SubmissionHistory({ title }: { title?: string | null }) {
  const { profile } = useAuth();
  const { t } = useI18n();
  const submissions = useUserSubmissions();

  return (
    <section className="embedded-system-block submission-history-block">
      {title ? <h3 className="section-label">{title}</h3> : null}
      {submissions.loading ? (
        <div className="card embedded-system-state">Загрузка заявок…</div>
      ) : null}
      {submissions.error ? (
        <div className="card form-error">{submissions.error}</div>
      ) : null}
      {!submissions.loading &&
      !submissions.error &&
      submissions.items.length === 0 ? (
        <div className="card embedded-system-state">
          {t("history:main:no_submissions")}
        </div>
      ) : null}
      {!submissions.loading && !submissions.error
        ? submissions.items.map((submission) => (
            <button
              type="button"
              key={submission.id}
              className="sub-card"
              onClick={() => void submissions.open(submission)}
            >
              <span>
                <span className="name">
                  {`${submission.form_name ?? t("word:submission")} #${submission.id}`}
                </span>
                <span className="meta">
                  {t("word:create_at")} {formatDateTime(submission.created_at)}
                </span>
              </span>
              <span className={`tag ${statusClass(submission.status)}`}>
                <span className="dot" />
                {statusLabel(submission.status, profile?.language_code)}
              </span>
            </button>
          ))
        : null}
      {submissions.selected ? (
        <SubmissionSheet
          submission={submissions.selected}
          lang={profile?.language_code}
          onClose={submissions.close}
        />
      ) : null}
    </section>
  );
}
