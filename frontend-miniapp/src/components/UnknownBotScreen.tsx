import { useEffect } from 'react'
import { getWebApp } from '@/max/bridge'

const CLOSE_DELAY_MS = 1500

interface UnknownBotScreenProps {
  insideMax: boolean
}

// Shown when bootstrap could not resolve which bot this mini-app instance belongs to (no `?bot=`
// param and nothing remembered on this device -- see `resolveBotIdentity()` in `lib/botSlug.ts`).
// Rendered instead of the normal app tree, before any API call would go out under an unintended
// bot's identity.
export function UnknownBotScreen({ insideMax }: UnknownBotScreenProps) {
  useEffect(() => {
    if (!insideMax) return
    const timer = setTimeout(() => {
      getWebApp()?.close?.()
    }, CLOSE_DELAY_MS)
    return () => clearTimeout(timer)
  }, [insideMax])

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        padding: 16,
        background: 'linear-gradient(180deg, var(--brand-50) 0%, var(--bg) 100%)',
      }}>
      <div
        style={{
          width: '100%',
          maxWidth: 380,
          background: 'var(--card)',
          border: '1px solid var(--line)',
          borderRadius: 20,
          boxShadow: 'var(--shadow)',
          padding: '36px 24px 28px',
          textAlign: 'center',
        }}>
        <p style={{ margin: 0, color: 'var(--ink-500)', fontSize: 14, lineHeight: 1.5 }}>
          {insideMax
            ? 'Не удалось определить бота. Приложение закроется — откройте его снова из чата бота.'
            : 'Откройте приложение через кнопку бота в MAX.'}
        </p>
      </div>
    </div>
  )
}
