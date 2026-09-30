import { getBotSlug } from "@/api/client";

function uuid(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0"));
  return `${hex.slice(0, 4).join("")}-${hex.slice(4, 6).join("")}-${hex.slice(6, 8).join("")}-${hex.slice(8, 10).join("")}-${hex.slice(10).join("")}`;
}

export function createAnalyticsEventId(): string {
  return uuid();
}

export function getAnalyticsSessionId(): string {
  const key = `platform.analytics.session.${getBotSlug()}`;
  const stored = sessionStorage.getItem(key);
  if (stored) return stored;
  const created = uuid();
  sessionStorage.setItem(key, created);
  return created;
}
