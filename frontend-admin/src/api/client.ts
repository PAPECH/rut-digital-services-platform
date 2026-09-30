import type { AdminProfile } from "@/api/types";
import { ADMIN_API_BASE } from "@/api/config";
import { apiErrorMessage } from "@/api/errorMessage";
import { getSelectedBotSlug } from "@/shared/tenant/selectedBotStorage";

let accessToken: string | null = null;
let refreshPromise: Promise<AdminSessionResponse> | null = null;

const csrfCookieName =
  import.meta.env.VITE_ADMIN_CSRF_COOKIE_NAME ?? "platform_admin_csrf";

export interface AdminSessionResponse {
  token: { access_token: string };
  admin: AdminProfile;
}

export function getToken(): string | null {
  return accessToken;
}

export function setToken(token: string | null): void {
  accessToken = token;
}

/** Decode JWT payload (no signature check — backend is the source of truth). */
export function decodeJwtPayload(
  token: string | null,
): Record<string, unknown> | null {
  if (!token) return null;
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const padded = part.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
}

export function getCurrentAdminId(): number | null {
  const payload = decodeJwtPayload(getToken());
  const value = payload?.["admin_id"];
  return typeof value === "number" ? value : null;
}

export interface ApiError extends Error {
  status: number;
  code?: string;
  detail?: unknown;
}

function readCookie(name: string): string | null {
  const encodedName = `${encodeURIComponent(name)}=`;
  const item = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(encodedName));
  return item ? decodeURIComponent(item.slice(encodedName.length)) : null;
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }

  if (!response.ok) {
    const payload = data as {
      error?: { message?: string; code?: string };
      detail?: { code?: string } | string;
    } | null;
    const error = new Error(apiErrorMessage(data, response.status)) as ApiError;
    error.status = response.status;
    error.code =
      payload?.error?.code ??
      (payload?.detail && typeof payload.detail === "object"
        ? payload.detail.code
        : undefined);
    error.detail = data;
    throw error;
  }
  return data as T;
}

async function rawRequest<T>(
  method: string,
  path: string,
  body?: unknown,
  extraHeaders?: Record<string, string>,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Bot-Slug": getSelectedBotSlug(),
    ...extraHeaders,
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const response = await fetch(`${ADMIN_API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: "include",
  });
  return parseResponse<T>(response);
}

export async function refreshAdminSession(): Promise<AdminSessionResponse> {
  if (refreshPromise) return refreshPromise;
  const csrfToken = readCookie(csrfCookieName);
  if (!csrfToken) throw new Error("Refresh-сессия отсутствует");

  refreshPromise = rawRequest<AdminSessionResponse>(
    "POST",
    "/auth/admin/refresh",
    undefined,
    {
      "X-CSRF-Token": csrfToken,
    },
  )
    .then((session) => {
      setToken(session.token.access_token);
      return session;
    })
    .catch((error) => {
      setToken(null);
      throw error;
    })
    .finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}

export async function logoutAdminSession(): Promise<void> {
  const csrfToken = readCookie(csrfCookieName);
  try {
    if (csrfToken) {
      await rawRequest<void>("POST", "/auth/admin/logout", undefined, {
        "X-CSRF-Token": csrfToken,
      });
    }
  } finally {
    setToken(null);
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  try {
    return await rawRequest<T>(method, path, body);
  } catch (error) {
    const apiError = error as ApiError;
    const isSessionEndpoint = path.startsWith("/auth/admin/");
    if (apiError.status !== 401 || isSessionEndpoint) throw error;
    await refreshAdminSession();
    return rawRequest<T>(method, path, body);
  }
}

async function rawBlobRequest(path: string): Promise<Blob> {
  const headers: Record<string, string> = {
    "X-Bot-Slug": getSelectedBotSlug(),
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const response = await fetch(`${ADMIN_API_BASE}${path}`, {
    headers,
    credentials: "include",
  });
  if (!response.ok) {
    const error = new Error(`Не удалось получить файл (${response.status})`) as ApiError;
    error.status = response.status;
    throw error;
  }
  return response.blob();
}

async function requestBlob(path: string): Promise<Blob> {
  try {
    return await rawBlobRequest(path);
  } catch (error) {
    if ((error as ApiError).status !== 401) throw error;
    await refreshAdminSession();
    return rawBlobRequest(path);
  }
}

async function rawFileRequest<T>(path: string, file: File): Promise<T> {
  const headers: Record<string, string> = {
    "X-Bot-Slug": getSelectedBotSlug(),
  };
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  const body = new FormData();
  body.append("file", file);
  // No Content-Type header: the browser sets `multipart/form-data; boundary=...` itself from the
  // FormData body, and setting it manually here would drop the boundary parameter.
  const response = await fetch(`${ADMIN_API_BASE}${path}`, {
    method: "POST",
    headers,
    body,
    credentials: "include",
  });
  return parseResponse<T>(response);
}

async function requestFile<T>(path: string, file: File): Promise<T> {
  try {
    return await rawFileRequest<T>(path, file);
  } catch (error) {
    if ((error as ApiError).status !== 401) throw error;
    await refreshAdminSession();
    return rawFileRequest<T>(path, file);
  }
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  del: <T>(path: string) => request<T>("DELETE", path),
  getBlob: (path: string) => requestBlob(path),
  postFile: <T>(path: string, file: File) => requestFile<T>(path, file),
};
