import { useEffect, useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'

function getInitData(): string | null {
  const hash = window.location.hash
  if (!hash) return null

  const params = new URLSearchParams(hash.substring(1))
  return params.get('initData')
}

export function LoginPage() {
  const { admin, loginWithInitData } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const init = getInitData() || params.get('initData')

    const system = (params.get('system') as 'max' | 'beavers' | null) ?? 'max'
    if (!init) return
    setBusy(true)
    void loginWithInitData(init, system)
      .catch((e) => setError(e?.message ?? 'Не удалось войти'))
      .finally(() => setBusy(false))
  }, [params, loginWithInitData, navigate])

  if (admin) return <Navigate to='/dashboard' replace />

  const onOpenMax = () => {
    const botUsername = import.meta.env.VITE_MAX_BOT_USERNAME
    window.location.href = `https://max.ru/${botUsername}?startapp=admin_login`
  }

  return (
    <div className='auth-screen'>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 16,
        }}>
        <div className='auth-card'>
          <img
            src='/logo-miit.png'
            alt='РУТ (МИИТ)'
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
          <h1 style={{ color: 'var(--brand)', margin: ' 25px 0' }}>Админ-панель ботов РУТ (МИИТ)</h1>
          <button
            className='btn btn-primary'
            style={{
              width: '100%',
              justifyContent: 'center',
              padding: '12px 16px',
            }}
            onClick={onOpenMax}
            disabled={busy}>
            {busy ? 'Входим…' : 'Войти через MAX'}
          </button>
          {error && (
            <div
              style={{
                marginTop: 16,
                padding: '10px 12px',
                borderRadius: 8,
                background: 'var(--st-rej-bg)',
                color: 'var(--st-rej-fg)',
                fontSize: 13,
                textAlign: 'left',
              }}>
              {error}
            </div>
          )}
          <div
            style={{
              marginTop: 20,
              fontSize: 12,
              color: 'var(--ink-400)',
              lineHeight: 1.5,
            }}>
            Войти можно, если администратор добавил вас в сотрудники или прислал ссылку-приглашение.
          </div>
        </div>
        <div style={{ fontSize: 12, color: 'var(--ink-300)' }}>Разработано в ВИШ c любовью ❤️</div>
      </div>
    </div>
  )
}
