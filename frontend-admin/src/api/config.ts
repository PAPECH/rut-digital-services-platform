/**
 * The admin API is deliberately same-origin.
 *
 * Both the Vite development server and the production nginx container proxy
 * `/api` to the backend. Keeping the browser on one origin lets HttpOnly
 * refresh cookies and the CSRF cookie survive page reloads without exposing
 * the access token to persistent browser storage.
 */
export const ADMIN_API_BASE = '/api'
const ADMIN_WEBSOCKET_BASE = ''

export function createAdminWebSocketUrl(path: string): URL {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = new URL(`${ADMIN_WEBSOCKET_BASE}${normalizedPath}`, window.location.origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url
}

export function resolveAdminAssetUrl(url: string): string {
  if (/^https?:\/\//i.test(url)) return url
  return new URL(url, window.location.origin).toString()
}
