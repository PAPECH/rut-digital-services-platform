import type {
  ProfileFieldDefinition,
  Submission,
  Submitter,
} from "@/api/types";
import {
  availableProfileDisplayFields,
  type ProfileDisplayField,
} from "@/entities/profile/model/profileDisplayFields";

export interface SubmissionProfileColumn {
  key: string;
  label: string;
  type: ProfileDisplayField["type"];
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function currentSubmitterValue(
  submitter: Submitter | null | undefined,
  key: string,
): unknown {
  if (!submitter || !(key in submitter)) return undefined;
  return submitter[key as keyof Submitter];
}

export function submissionProfileValue(
  submission: Submission,
  key: string,
): unknown {
  const snapshot = asRecord(submission.profile_snapshot);
  if (snapshot[key] !== undefined && snapshot[key] !== null) return snapshot[key];

  const local = asRecord(snapshot.bot_local_data);
  if (local[key] !== undefined && local[key] !== null) return local[key];

  const shared = asRecord(snapshot.shared_data);
  if (shared[key] !== undefined && shared[key] !== null) return shared[key];

  return currentSubmitterValue(submission.submitter, key);
}

export function submissionFullName(submission: Submission): string {
  const parts = ["last_name", "first_name", "patronymic"]
    .map((key) => submissionProfileValue(submission, key))
    .filter((value): value is string => typeof value === "string" && Boolean(value.trim()));
  if (parts.length) return parts.join(" ");
  return submission.submitter?.username ?? "—";
}

export function submissionProfileColumns(
  profileSchema: ProfileFieldDefinition[],
): SubmissionProfileColumn[] {
  return availableProfileDisplayFields(profileSchema).filter(
    (field) => field.key !== "full_name",
  );
}

export function submissionTableProfileColumns(
  profileSchema: ProfileFieldDefinition[],
  selectedKeys: string[],
): SubmissionProfileColumn[] {
  const selected = new Set(selectedKeys);
  return availableProfileDisplayFields(profileSchema).filter((field) =>
    selected.has(field.key),
  );
}

export function formatSubmissionProfileValue(
  value: unknown,
  type?: SubmissionProfileColumn["type"],
): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Да" : "Нет";
  if (type === "date" && typeof value === "string") {
    const parsed = new Date(`${value.slice(0, 10)}T00:00:00`);
    if (!Number.isNaN(parsed.getTime())) return parsed.toLocaleDateString("ru-RU");
  }
  if (Array.isArray(value)) return value.map(String).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
