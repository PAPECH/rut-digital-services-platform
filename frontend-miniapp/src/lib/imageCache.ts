/**
 * In-memory (JS heap, not browser HTTP cache) image cache. Exists because the mini-app runs
 * embedded in a `credentialless` iframe inside the MAX web client, and Yandex Browser specifically
 * has been observed to not persist the regular HTTP cache for resources loaded that way -- every
 * navigation back to a page with a category image re-triggers a full network download regardless
 * of Cache-Control, even though the same page's own JS/React state clearly survives the
 * navigation (confirmed: no full-app reload flicker, just the image). Since the browser's HTTP
 * cache is the thing that's unreliable here, not this document's own JS memory, fetching the bytes
 * once ourselves and holding the result as a Blob object URL sidesteps the browser cache entirely.
 *
 * Object URLs are scoped to this document and stay valid for as long as it's alive, which is
 * exactly the lifetime we want them to have (the whole app session) -- so entries are never
 * revoked; the number of distinct category images per bot is small enough that this isn't a real
 * memory concern.
 */

const cache = new Map<string, string>()
const inFlight = new Map<string, Promise<string>>()

function fetchAsObjectUrl(url: string): Promise<string> {
  const promise = fetch(url)
    .then((res) => {
      if (!res.ok) throw new Error(`image fetch failed: ${res.status}`)
      return res.blob()
    })
    .then((blob) => {
      const objectUrl = URL.createObjectURL(blob)
      cache.set(url, objectUrl)
      return objectUrl
    })
    .finally(() => {
      inFlight.delete(url)
    })
  inFlight.set(url, promise)
  return promise
}

/** Cached object URL for `url` if already loaded, synchronously -- for the common case where
 * warmImageCache() already finished by the time something wants to render it. */
export function getCachedImageUrl(url: string | null | undefined): string | undefined {
  if (!url) return undefined
  return cache.get(url)
}

/** Resolves once the image is available as an object URL, fetching it if necessary. Safe to call
 * repeatedly for the same URL -- concurrent/repeat calls share the one in-flight fetch. */
export function loadImage(url: string): Promise<string> {
  return cache.has(url) ? Promise.resolve(cache.get(url)!) : (inFlight.get(url) ?? fetchAsObjectUrl(url))
}

/** Fire-and-forget warmup for a batch of URLs (e.g. the whole catalog's category images), called
 * once as soon as they're known so they're already cached by the time the user navigates to them. */
export function warmImageCache(urls: Iterable<string | null | undefined>): void {
  for (const url of urls) {
    if (!url || cache.has(url) || inFlight.has(url)) continue
    void loadImage(url).catch(() => undefined)
  }
}
