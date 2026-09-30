import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/AuthProvider'
import { Icon } from '@/components/Icon'
import { useBotSelection } from '@/features/bot-selection/model/BotSelectionContext'
import { useI18n } from '@/i18n'
import type { NavigationItem } from '@/widgets/admin-shell/model/navigation'
import { useTicketsOverview } from '@/widgets/admin-shell/model/useTicketsOverview'
import { AdminAccount } from '@/widgets/admin-shell/ui/AdminAccount'
import { BotSwitcher } from '@/widgets/admin-shell/ui/BotSwitcher'
import { AdminNavigation } from '@/widgets/admin-shell/ui/AdminNavigation'
import { DesktopAdminNavigation } from '@/widgets/admin-shell/ui/DesktopAdminNavigation'

export function AdminShell({ children }: { children: React.ReactNode }) {
  const { admin, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { selectedSlug } = useBotSelection()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const ticketsCount = useTicketsOverview(Boolean(admin), selectedSlug)
  const { t, lang, setLang } = useI18n()

  useEffect(() => setMobileMenuOpen(false), [location.pathname])

  const items = useMemo<NavigationItem[]>(() => {
    const result: NavigationItem[] = [
      { to: '/dashboard', label: t('nav.dashboard'), icon: <Icon.Dashboard /> },
      { to: '/submissions', label: 'Формы', icon: <Icon.Forms /> },
      { to: '/form-tests', label: 'Тесты', icon: <Icon.Forms /> },
      {
        to: '/tickets',
        label: t('nav.tickets'),
        icon: <Icon.Tickets />,
        badge: ticketsCount || undefined,
      },
      { to: '/users', label: t('nav.users'), icon: <Icon.Users /> },
      { to: '/content', label: 'Контент', icon: <Icon.Builder /> },
      { to: '/news', label: 'Новости', icon: <Icon.Bell /> },
      { to: '/files', label: 'Файлы', icon: <Icon.Paperclip /> },
    ]
    if (admin?.role === 'admin' || admin?.role === 'platform_admin') {
      result.push(
        { to: '/capabilities', label: 'Возможности', icon: <Icon.Settings /> },
        { to: '/campaigns', label: 'Кампании', icon: <Icon.ExternalLink /> },
        { to: '/builder', label: t('nav.builder'), icon: <Icon.Builder /> },
        { to: '/faq', label: t('nav.faq'), icon: <Icon.Forms /> },
        { to: '/kb', label: t('nav.kb'), icon: <Icon.Forms /> },
        { to: '/admins', label: t('nav.admins'), icon: <Icon.Users /> },
        { to: '/audit', label: 'Журнал', icon: <Icon.Forms /> },
        {
          to: '/bot-settings',
          label: t('nav.bot_settings'),
          icon: <Icon.Settings />,
        },
      )
    }
    if (admin?.role === 'platform_admin') {
      result.push({
        to: '/platform/bots',
        label: 'Боты',
        icon: <Icon.Settings />,
      })
    }
    result.push({ to: '/guide', label: 'Инструкции', icon: <Icon.Info /> })
    return result
  }, [admin?.role, t, ticketsCount])

  if (!admin) return <>{children}</>

  const onLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }
  const roleLabel = admin.role === 'platform_admin' ? 'Админ платформы' : t(`role.${admin.role}`)
  const account = (
    <AdminAccount
      admin={admin}
      language={lang}
      roleLabel={roleLabel}
      logoutLabel={t('action.logout')}
      onToggleLanguage={() => setLang(lang === 'ru' ? 'en' : 'ru')}
      onLogout={() => void onLogout()}
    />
  )

  return (
    <div className='app'>
      <nav className='navbar'>
        <button
          className='mobile-menu-toggle icon-btn'
          aria-label='Открыть меню'
          aria-expanded={mobileMenuOpen}
          onClick={() => setMobileMenuOpen((open) => !open)}>
          <span className='ico'>{mobileMenuOpen ? <Icon.X /> : <Icon.Menu />}</span>
        </button>
        <div className='brand'>
          <div className='name'>
            <img className='brand-logo' src='/logo-miit-white.png' alt='РУТ (МИИТ)' />
          </div>
        </div>
        <div className='desktop-bot-switcher'>
          <BotSwitcher />
        </div>
        <div className='desktop-navigation'>
          <DesktopAdminNavigation items={items} />
        </div>
        <div className='desktop-account'>{account}</div>
      </nav>

      {mobileMenuOpen ? (
        <>
          <button
            className='mobile-nav-backdrop'
            aria-label='Закрыть меню'
            onClick={() => setMobileMenuOpen(false)}
          />
          <aside className='mobile-nav' aria-label='Навигация админ-панели'>
            <BotSwitcher />
            <AdminNavigation items={items} onNavigate={() => setMobileMenuOpen(false)} />
            {account}
          </aside>
        </>
      ) : null}

      <main key={selectedSlug}>{children}</main>
    </div>
  )
}
