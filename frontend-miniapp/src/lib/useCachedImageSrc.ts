import { useEffect, useState } from 'react'

import { getCachedImageUrl, loadImage } from '@/lib/imageCache'

/**
 * Returns an object-URL src for `url` once it's available from the in-memory image cache
 * (see imageCache.ts), falling back to `null` while it's still loading. Callers that want to show
 * *something* immediately (rather than nothing until the fetch resolves) should fall back to the
 * raw `url` themselves -- in practice the catalog-wide warmup means this resolves synchronously
 * from cache almost every time a component actually mounts.
 */
export function useCachedImageSrc(url: string | null | undefined): string | null {
  const [src, setSrc] = useState<string | null>(() => getCachedImageUrl(url) ?? null)

  useEffect(() => {
    if (!url) {
      setSrc(null)
      return
    }
    const cached = getCachedImageUrl(url)
    if (cached) {
      setSrc(cached)
      return
    }
    let active = true
    loadImage(url)
      .then((objectUrl) => {
        if (active) setSrc(objectUrl)
      })
      .catch(() => undefined)
    return () => {
      active = false
    }
  }, [url])

  return src
}
