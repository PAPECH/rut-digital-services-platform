import { useMemo } from "react";

import type { Submission } from "@/api/types";
import { submissionFileFieldKeys } from "@/features/submission-attachments/model/submissionFileFields";
import { useSubmissionAttachments } from "@/features/submission-attachments/model/useSubmissionAttachments";
import { SubmissionAttachmentList } from "@/features/submission-attachments/ui/SubmissionAttachmentList";
import { resolveOptionLabel, resolveOptionLabels } from "@/features/submissions/lib/resolveOptionLabel";
import { useI18n } from "@/i18n";
import { formatDateTime, statusClass, statusLabel } from "@/lib/status";

export function SubmissionSheet({
  submission,
  lang,
  onClose,
}: {
  submission: Submission;
  lang: string | null | undefined;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const attachments = useSubmissionAttachments(submission.id);
  const snapshotFileFields = useMemo(
    () => submissionFileFieldKeys(submission.form_snapshot),
    [submission.form_snapshot],
  );

  return (
    <div className="submission-sheet" role="dialog" aria-modal="true">
      <button
        type="button"
        className="submission-sheet__backdrop"
        aria-label="Закрыть заявку"
        onClick={onClose}
      />
      <div className="submission-sheet__body">
        <div className="submission-sheet__head">
          <div>
            <strong>{`${submission.form_name ?? t("word:submission")} #${submission.id}`}</strong>
            <small>
              {t("word:create_at")} {formatDateTime(submission.created_at)}
            </small>
          </div>
          <button
            type="button"
            className="submission-sheet__close"
            onClick={onClose}
            aria-label="Закрыть"
          >
            ×
          </button>
        </div>

        <span className={`tag ${statusClass(submission.status)}`}>
          <span className="dot" />
          {statusLabel(submission.status, lang)}
        </span>

        <h4 className="submission-sheet__section-title">{t("word:form_data")}</h4>
        {Object.entries(submission.values).map(([key, value]) => {
          const fieldAttachments = attachments.byField.get(key) ?? [];
          const isFileField =
            snapshotFileFields.has(key) || attachments.byField.has(key);
          return (
            <div key={key} className={`row${isFileField ? " row--files" : ""}`}>
              <span className="lbl">
                {submission.field_labels?.[key] ?? `${t("word:field")} #${key}`}
              </span>
              {fieldAttachments.length ? (
                <SubmissionAttachmentList items={fieldAttachments} />
              ) : isFileField && attachments.loading ? (
                <span className="history-files-state">
                  {t("history:files:loading")}
                </span>
              ) : isFileField ? (
                <span className="history-files-state history-files-error">
                  {t("history:files:unavailable")}
                </span>
              ) : (
                <span className="val">{renderValue(value, key, submission.form_snapshot)}</span>
              )}
            </div>
          );
        })}
        {attachments.error ? (
          <div className="history-files-state history-files-error">
            {attachments.error}
          </div>
        ) : null}

        <h4 className="submission-sheet__section-title">
          {t("history:main:status_history")}
        </h4>
        {(submission.history ?? []).map((history) => (
          <div key={history.id} className="row">
            <div>
              {history.from_status
                ? `${statusLabel(history.from_status, lang)} → `
                : ""}
              <b>{statusLabel(history.to_status, lang)}</b>
              {history.comment ? (
                <div className="submission-sheet__comment">{history.comment}</div>
              ) : null}
            </div>
            <span className="submission-sheet__date">
              {formatDateTime(history.changed_at)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function renderValue(
  value: unknown,
  fieldKey: string,
  formSnapshot: Record<string, unknown>,
): React.ReactNode {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Да" : "Нет";
  if (Array.isArray(value)) return resolveOptionLabels(formSnapshot, fieldKey, value);
  if (typeof value === "string") return resolveOptionLabel(formSnapshot, fieldKey, value);
  return String(value);
}
