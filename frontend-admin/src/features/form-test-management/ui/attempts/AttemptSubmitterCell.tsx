import { Avatar } from "@/components/Avatar";
import type { AttemptSubmitter } from "@/entities/form-test/model/types";

export function attemptSubmitterName(submitter: AttemptSubmitter | null, userId: number): string {
  if (!submitter) return `#${userId}`;
  const parts = [submitter.last_name, submitter.first_name, submitter.patronymic].filter(
    (part): part is string => Boolean(part && part.trim()),
  );
  if (parts.length) return parts.join(" ");
  return submitter.username ? `@${submitter.username}` : `#${userId}`;
}

/** Clickable submitter cell opening `UserCardPanel`, mirroring `SubmissionsPage.tsx`'s
 * `SubmitterCell` for form submissions (Task 077). */
export function AttemptSubmitterCell({
  userId,
  submitter,
  onOpen,
}: {
  userId: number;
  submitter: AttemptSubmitter | null;
  onOpen: (userId: number) => void;
}) {
  const name = attemptSubmitterName(submitter, userId);
  return (
    <button type="button" className="submission-user-link" onClick={() => onOpen(userId)}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Avatar size="sm" user={{ photo_url: submitter?.photo_url, fullName: name }} />
        <div>
          <div style={{ fontWeight: 600 }}>{name}</div>
          {submitter?.username && (
            <div style={{ fontSize: 11.5, color: "var(--ink-400)" }}>@{submitter.username}</div>
          )}
        </div>
      </div>
    </button>
  );
}
