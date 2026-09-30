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
      return "new";
  }
}

export function statusLabel(
  status: SubmissionStatus,
  lang: string | null = "ru",
): string {
  const isEn = lang && !lang.toLowerCase().startsWith("ru");
  switch (status) {
    case "new":
      return isEn ? "New" : "Новая";
    case "in_work":
      return isEn ? "In progress" : "В работе";
    case "done":
      return isEn ? "Done" : "Завершено";
    case "rejected":
      return isEn ? "Rejected" : "Отклонено";
  }
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
