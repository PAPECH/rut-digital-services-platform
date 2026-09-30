const PERSIST_KEY = 'mfc.miniapp.lastBotSlug'

let botSlug: string | null = null

export function setBotSlug(slug: string) {
  botSlug = slug
}

// Returns the in-memory slug already resolved this session, or `'default'` as a last-resort
// fallback for callers that run before/without going through `resolveBotIdentity()` (e.g. the
// `/preview/:token` bootstrap, which sets the slug itself before anything else runs). In normal
// production flow this fallback is unreachable, since `resolveBotIdentity()` gates rendering.
export function getApiBotSlug(): string {
  return botSlug ?? 'default'
}

function readPersistedBotSlug(): string | null {
  try {
    return localStorage.getItem(PERSIST_KEY)
  } catch {
    return null
  }
}

function persistBotSlug(slug: string): void {
  try {
    localStorage.setItem(PERSIST_KEY, slug)
  } catch {
    // localStorage unavailable (private mode, storage blocked) -- continuity fallback just won't
    // work on this device; the app still functions via `?bot=` every time.
  }
}

export type BotIdentityResolution = { status: 'resolved'; slug: string } | { status: 'unknown' }

/**
 * Resolution order: explicit `?bot=` in the URL (authoritative, persisted for next time) -> the
 * slug this device last resolved successfully -> a dev-build-only `'default'` convenience -> unknown.
 *
 * Must run once at bootstrap, before any provider that could issue an API call mounts, so the
 * mini-app never sends a request under an unintended bot's identity (see Task 034).
 */
export function resolveBotIdentity(search: string = window.location.search): BotIdentityResolution {
  const fromQuery = new URLSearchParams(search).get('bot')
  if (fromQuery) {
    setBotSlug(fromQuery)
    persistBotSlug(fromQuery)
    return { status: 'resolved', slug: fromQuery }
  }

  const persisted = readPersistedBotSlug()
  if (persisted) {
    setBotSlug(persisted)
    return { status: 'resolved', slug: persisted }
  }

  if (import.meta.env.DEV) {
    setBotSlug('default')
    return { status: 'resolved', slug: 'default' }
  }

  return { status: 'unknown' }
}
