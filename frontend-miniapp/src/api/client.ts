import { apiErrorMessage } from '@/api/errorMessage'
import { getApiBotSlug } from '@/lib/botSlug'

const apiRoot = `${(import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')}/api`

export function getBotSlug(): string {
  // `.get('bot')` returning null (no `?bot=` param -- the normal case for every in-app route
  // after the first navigation, since `<Link to="/content/...">` never carries query params) was
  // being coalesced to `''` *before* the `??` below ever saw it, so the `getApiBotSlug()` fallback
  // was permanently dead code and every request after the first one silently went out with an
  // empty `X-Bot-Slug` header. `!raw` (covering both null and empty-string) is what actually
  // means "no usable query override" here.
  const raw = new URLSearchParams(window.location.search).get('bot')
  if (!raw) return getApiBotSlug()
  return raw.split('?')[0]
}

export function getToken(): string | null {
  return sessionStorage.getItem(`mfc.miniapp.token.${getBotSlug()}`)
}

export function setToken(token: string | null): void {
  const key = `mfc.miniapp.token.${getBotSlug()}`
  if (token) sessionStorage.setItem(key, token)
  else sessionStorage.removeItem(key)
}

export interface ApiError extends Error {
  status: number
  code?: string
  detail?: unknown
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const isFormData = body instanceof FormData
  const headers: Record<string, string> = { 'X-Bot-Slug': getBotSlug() }
  if (!isFormData) headers['Content-Type'] = 'application/json'
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${apiRoot}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
  })

  if (res.status === 204) return undefined as T

  const text = await res.text()
  let data: unknown = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }

  if (!res.ok) {
    const envelope =
      typeof data === 'object' && data !== null ? (data as { error?: { code?: string } }) : null
    const err = new Error(apiErrorMessage(data, res.status)) as ApiError
    err.status = res.status
    err.code = envelope?.error?.code
    err.detail = data
    throw err
  }
  return data as T
}

async function requestBlob(path: string): Promise<Blob> {
  const headers: Record<string, string> = { 'X-Bot-Slug': getBotSlug() }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${apiRoot}${path}`, { headers })
  if (!res.ok) {
    const err = new Error(
      res.status === 404 ? 'Файл не найден' : `Не удалось получить файл (${res.status})`,
    ) as ApiError
    err.status = res.status
    throw err
  }
  return res.blob()
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
  upload: <T>(path: string, body: FormData) => request<T>('POST', path, body),
  getBlob: (path: string) => requestBlob(path),
}
