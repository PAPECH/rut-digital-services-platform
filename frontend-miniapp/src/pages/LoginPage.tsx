export function LoginPage() {
  const botUsername = (import.meta.env.VITE_MAX_BOT_USERNAME as string) || 'rut_mfc_test_bot'

  const onOpenMax = () => {
    window.location.href = `https://max.ru/${botUsername}?startapp=student_login`
  }

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
        <img src='logo-miit.png' style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
        <h1 style={{ margin: '0 0 4px', fontSize: 20, letterSpacing: '-.01em' }}>БОТЫ · РУТ МИИТ</h1>
        <p style={{ margin: '0 0 24px', color: 'var(--ink-400)', fontSize: 13 }}>
          Авторизация выполняется через MAX. Откройте бота, чтобы продолжить.
        </p>
        <button className='btn btn-primary' onClick={onOpenMax}>
          Войти через MAX
        </button>
        <p
          style={{
            marginTop: 18,
            fontSize: 11.5,
            color: 'var(--ink-400)',
            lineHeight: 1.5,
          }}>
          После входа вы автоматически вернётесь на этот сайт. Все данные о заявках и справках доступны только
          владельцу аккаунта.
        </p>
      </div>
    </div>
  )
}
