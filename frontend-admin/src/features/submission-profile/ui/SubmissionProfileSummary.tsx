import type { ProfileFieldDefinition, Submission } from "@/api/types";
import {
  formatSubmissionProfileValue,
  submissionFullName,
  submissionProfileColumns,
  submissionProfileValue,
} from "@/features/submission-profile/model/submissionProfile";

export function SubmissionProfileSummary({
  submission,
  profileSchema,
  onOpenUser,
}: {
  submission: Submission;
  profileSchema: ProfileFieldDefinition[];
  onOpenUser: (() => void) | null;
}) {
  const columns = submissionProfileColumns(profileSchema);
  return (
    <section
      className={`submission-profile-summary${onOpenUser ? " submission-profile-summary--clickable" : ""}`}
      onClick={onOpenUser ?? undefined}
      title={onOpenUser ? "Открыть карточку пользователя" : undefined}
    >
      <div className="submission-profile-summary__heading">
        <span>Заявитель</span>
        <strong>{submissionFullName(submission)}</strong>
      </div>
      <dl className="submission-profile-summary__grid">
        {columns.map((column) => (
          <div key={column.key}>
            <dt>{column.label}</dt>
            <dd>
              {formatSubmissionProfileValue(
                submissionProfileValue(submission, column.key),
                column.type,
              )}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
