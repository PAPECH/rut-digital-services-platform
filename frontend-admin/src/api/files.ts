import { getToken } from "@/api/client";
import { ADMIN_API_BASE } from "@/api/config";
import { getSelectedBotSlug } from "@/shared/tenant/selectedBotStorage";

export interface UploadedFile {
  id: number;
  url: string;
  name: string;
  mime: string;
  size_bytes: number;
}

export async function uploadFile(file: File, purpose?: string): Promise<UploadedFile> {
  const fd = new FormData();
  fd.append("file", file);
  if (purpose) fd.append("purpose", purpose);

  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  headers["X-Bot-Slug"] = getSelectedBotSlug();

  const res = await fetch(`${ADMIN_API_BASE}/files`, {
    method: "POST",
    headers,
    body: fd,
    credentials: "include",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Upload failed (${res.status})`);
  }
  return res.json();
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} Б`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} КБ`;
  return `${(n / (1024 * 1024)).toFixed(1)} МБ`;
}

export function isImageMime(mime?: string | null): boolean {
  return Boolean(mime && mime.startsWith("image/"));
}

/** Uppercased extension without the dot, e.g. "instruction.pdf" -> "PDF"; "" if there is none. */
export function fileExtension(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot > 0 && dot < name.length - 1 ? name.slice(dot + 1).toUpperCase() : "";
}
