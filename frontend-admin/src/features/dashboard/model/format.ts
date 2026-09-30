export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatDuration(seconds: number): string {
  if (!seconds) return "—";
  if (seconds < 60) return `${seconds} сек`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes} мин`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    const rest = minutes % 60;
    return rest ? `${hours} ч ${rest} мин` : `${hours} ч`;
  }
  const days = Math.floor(hours / 24);
  const restHours = hours % 24;
  return restHours ? `${days} д ${restHours} ч` : `${days} д`;
}

export function deltaPercent(current: number, previous: number): number | null {
  if (!previous) return null;
  return ((current - previous) / previous) * 100;
}

export function formatDelta(current: number, previous: number): string | null {
  if (!previous) return current ? "новое" : null;
  const delta = deltaPercent(current, previous);
  if (delta === null) return null;
  const rounded = Math.round(delta);
  return `${rounded > 0 ? "+" : ""}${rounded}%`;
}

export const DASHBOARD_COLORS = [
  "#1B365D",
  "#3E6BAA",
  "#2E8B57",
  "#C77700",
  "#7A4D9C",
  "#2C7A7B",
  "#9B4B5A",
];
