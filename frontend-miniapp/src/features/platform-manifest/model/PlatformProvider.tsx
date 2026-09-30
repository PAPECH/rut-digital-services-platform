import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { api } from '@/api/client'
import type { AppManifest } from '@/api/types'
import { setBotSlug } from '@/lib/botSlug'

interface PlatformState {
  manifest: AppManifest | null
  loading: boolean
  error: string | null
}

const PlatformContext = createContext<PlatformState | null>(null)

export function PlatformProvider({ children }: { children: ReactNode }) {
  const [manifest, setManifest] = useState<AppManifest | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    api
      .get<AppManifest>('/manifest')
      .then((result) => {
        if (active) setManifest(result)
      })
      .catch((reason: Error) => {
        if (active) setError(reason.message || 'Не удалось загрузить конфигурацию бота')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])
  if (manifest) setBotSlug(manifest.bot.slug)
  const value = useMemo(() => ({ manifest, loading, error }), [manifest, loading, error])
  return <PlatformContext.Provider value={value}>{children}</PlatformContext.Provider>
}

export function usePlatform(): PlatformState {
  const value = useContext(PlatformContext)
  if (!value) throw new Error('usePlatform must be used within PlatformProvider')
  return value
}
