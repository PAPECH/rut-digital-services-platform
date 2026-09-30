import type { SubmissionStatus } from "@/api/types";

export function statusClass(status: SubmissionStatus): string {
  switch (status) {
    case "new":
      return "new";
    case "in_work":
      return "work";
    case "done":
      return "done";
    case "rejected":
      return "rej";
    default:
      return "neutral";
  }
}

export function statusLabel(status: SubmissionStatus): string {
  switch (status) {
    case "new":
      return "Новая";
    case "in_work":
      return "В работе";
    case "done":
      return "Завершено";
    case "rejected":
      return "Отклонено";
    default:
      return status;
  }
}

// Action-verb copy for the buttons that trigger a status transition — distinct from
// `statusLabel`, which names the resulting state for read-only badges/history/filters.
export function actionLabel(status: SubmissionStatus): string {
  switch (status) {
    case "in_work":
      return "Взять в работу";
    case "done":
      return "Завершить";
    case "rejected":
      return "Отклонить";
    default:
      return statusLabel(status);
  }
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function formatDuration(seconds: number): string {
  if (!seconds) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h >= 24) {
    const d = Math.floor(h / 24);
    return `${d} д ${h % 24} ч`;
  }
  if (h > 0) return `${h} ч ${m} мин`;
  return `${m} мин`;
}

export function initials(
  name: string | null | undefined,
  fallback = "?",
): string {
  if (!name) return fallback;
  return name
    .split(" ")
    .slice(0, 2)
    .map((s) => s[0] || "")
    .join("")
    .toUpperCase();
}
