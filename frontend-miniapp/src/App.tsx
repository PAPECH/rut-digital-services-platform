import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth } from '@/auth/AuthProvider'
import { ConsentGateScreen } from '@/features/consent/ui/ConsentGateScreen'
import { PolicyScreen } from '@/features/consent/ui/PolicyScreen'
import { acceptConsent as acceptConsentCall } from '@/features/consent/api/consentApi'
import { POLICY_START_PARAM } from '@/features/consent/model/policyStartParam'
import { Topbar } from '@/components/Topbar'
import { BottomNav } from '@/components/BottomNav'
import { HomePage } from '@/pages/HomePage'
import { SubmissionsPage } from '@/pages/SubmissionsPage'
import { SubmitPage } from '@/pages/SubmitPage'
import { TestPage } from '@/pages/TestPage'
import { ServicesPage } from '@/pages/ServicesPage'
import { FaqPage } from '@/pages/FaqPage'
import { NewsPage } from '@/pages/NewsPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { ContentCategoryPage } from '@/pages/ContentCategoryPage'
import { CapabilityPage } from '@/pages/CapabilityPage'
import { usePlatform } from '@/features/platform-manifest/model/PlatformProvider'
import { useContentCatalog } from '@/features/content/model/ContentCatalogProvider'
import { MaintenanceNotice, MaintenanceScreen } from '@/features/platform-manifest/ui/MaintenanceNotice'
import { trackAnalyticsEventOnce } from '@/features/analytics/api/analyticsApi'
import { reportCampaignLinkOpenOnce } from '@/features/campaign-links/api/campaignLinksApi'

import { openLink, setupBackButton, getWebApp, getStartParam } from '@/max/bridge'

export function App() {
  const {
    profile,
    loading,
    error,
    insideMax,
    needsRedirect,
    refresh,
    consentRequired,
    consentBusy,
    consentError,
    acceptGateConsent,
  } = useAuth()
  const platform = usePlatform()
  const contentCatalog = useContentCatalog()
  const navigate = useNavigate()
  const location = useLocation()
  const [reconsentBusy, setReconsentBusy] = useState(false)
  const [reconsentError, setReconsentError] = useState<string | null>(null)
  // A local-state overlay, not a route: it must be reachable from the consent gate (which
  // renders before <Routes> even mounts, see the early returns below) as well as from
  // ProfilePage, and closing it must always land back on whichever of those was showing --
  // trivial with a toggle, would need real route/history plumbing otherwise.
  const [showPolicy, setShowPolicy] = useState(false)

  const handleReconsent = async () => {
    setReconsentBusy(true)
    setReconsentError(null)
    try {
      await acceptConsentCall()
      await refresh()
    } catch (e) {
      setReconsentError((e as Error)?.message ?? 'Не удалось подтвердить согласие')
    } finally {
      setReconsentBusy(false)
    }
  }

  // Bot's OpenAppButton for the policy prompt launches straight into this screen (see
  // bot/app/main.py's _build_policy_button) -- checked unconditionally on mount, not gated
  // on profile/platform having loaded, since the consent gate itself (below) can render
  // before any of that finishes (a brand-new identity has no User row yet).
  useEffect(() => {
    if (getStartParam() === POLICY_START_PARAM) setShowPolicy(true)
  }, [])

  // Deep-linked into the policy screen while consent is already active: land the underlying
  // route on /profile first, so "Назад" returns there instead of the Home page.
  useEffect(() => {
    if (showPolicy && profile?.consent_is_active && location.pathname !== '/profile') {
      navigate('/profile', { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showPolicy, profile?.consent_is_active])

  useEffect(() => {
    const color = platform.manifest?.bot.branding.primary_color
    if (typeof color === 'string' && /^#[0-9a-fA-F]{6}$/.test(color)) {
      document.documentElement.style.setProperty('--brand', color)
    } else {
      document.documentElement.style.removeProperty('--brand')
    }
  }, [platform.manifest?.bot.branding.primary_color])

  useEffect(() => {
    const onRoot = location.pathname === '/'
    setupBackButton(!onRoot, () => navigate(-1))
  }, [location.pathname, navigate])

  // The app scrolls the document itself (no fixed-height inner scroll container), and React
  // Router does not reset that scroll position on navigation -- without this, opening a category
  // page after scrolling down in a previous one starts already scrolled down.
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [location.pathname])

  useEffect(() => {
    if (
      platform.loading ||
      platform.error ||
      !platform.manifest ||
      loading ||
      error ||
      !profile ||
      contentCatalog.loading ||
      contentCatalog.error ||
      profile.ban_app
    )
      return
    trackAnalyticsEventOnce(`app-open:${platform.manifest.bot.id}`, {
      action_type: 'app_open',
      source_surface: 'direct',
    })
    const startParam = getStartParam()
    if (startParam && startParam !== POLICY_START_PARAM) reportCampaignLinkOpenOnce(startParam)
  }, [
    contentCatalog.error,
    contentCatalog.loading,
    error,
    loading,
    platform.error,
    platform.loading,
    platform.manifest,
    profile,
  ])

  if (showPolicy) {
    // Overrides every other screen below, including the consent gate and the redirect/
    // maintenance screens -- viewing the policy is meant to work regardless of what other
    // state the app is in, same reasoning as the notice text being public.
    return <PolicyScreen onBack={() => setShowPolicy(false)} />
  }

  if (needsRedirect) {
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

          <p
            style={{
              margin: '0 0 24px',
              color: 'var(--ink-400)',
              fontSize: 13,
            }}>
            Подтвердите вход в админ-панель бота.
          </p>
          <button
            className='btn btn-primary'
            onClick={() => {
              openLink(needsRedirect)
              getWebApp()?.close?.()
            }}>
            Авторизоваться в панели
          </button>
        </div>
      </div>
    )
  }

  if (consentRequired) {
    // Takes precedence over everything below (platform loading/maintenance included --
    // see docs/tasks/064, "consent gate is independent of and takes precedence over
    // maintenance mode") because it communicates something about this person's standing,
    // not a temporary platform state.
    return (
      <ConsentGateScreen
        busy={consentBusy}
        error={consentError}
        onAccept={() => void acceptGateConsent()}
        onShowPolicy={() => setShowPolicy(true)}
      />
    )
  }

  if (platform.loading) {
    return (
      <>
        <Topbar />
        <div className='screen'>
          <div className='skeleton' style={{ width: '60%', height: 28 }} />
          <div className='skeleton' style={{ width: '100%', height: 80, marginTop: 12 }} />
        </div>
      </>
    )
  }

  if (platform.error || !platform.manifest) {
    return (
      <>
        <Topbar />
        <div className='screen platform-error'>
          <h1 className='screen-title'>Сервис временно недоступен</h1>
          <p>{platform.error || 'Не удалось определить конфигурацию бота.'}</p>
        </div>
      </>
    )
  }

  if (platform.manifest.maintenance?.mode === 'full_stop') {
    return <MaintenanceScreen policy={platform.manifest.maintenance} />
  }

  if (loading) {
    return (
      <>
        <Topbar />
        <div className='screen'>
          <div className='skeleton' style={{ width: '60%', height: 28 }} />
          <div style={{ marginTop: 12 }}>
            <div className='skeleton' style={{ width: '100%', height: 80 }} />
          </div>
        </div>
      </>
    )
  }

  if (error || !profile) {
    return (
      <>
        <Topbar />
        <div className='screen' style={{ textAlign: 'center', padding: 32 }}>
          <h1 className='screen-title' style={{ marginTop: 32 }}>
            Не удалось войти
          </h1>
          <p style={{ color: 'var(--ink-500)', fontSize: 14 }}>
            {error ??
              (insideMax
                ? 'Авторизация недоступна. Откройте мини-приложение из чата MAX.'
                : `Авторизация недоступна. Попробуйте обновить страницу.  Ошибка: ${error}`)}
          </p>
        </div>
      </>
    )
  }

  if (contentCatalog.loading) {
    return (
      <>
        <Topbar />
        <div className='screen'>
          <div className='skeleton' style={{ width: '60%', height: 28 }} />
          <div className='skeleton' style={{ width: '100%', height: 80, marginTop: 12 }} />
        </div>
      </>
    )
  }

  if (contentCatalog.error) {
    return (
      <>
        <Topbar />
        <div className='screen platform-error'>
          <h1 className='screen-title'>Не удалось загрузить приложение</h1>
          <p>{contentCatalog.error}</p>
          <button className='btn btn-primary' onClick={() => void contentCatalog.reload()}>
            Повторить
          </button>
        </div>
      </>
    )
  }

  if (profile.ban_app) {
    return (
      <div
        style={{
          minHeight: '100vh',
          background: '#b91c1c',
          color: '#fff',
          display: 'grid',
          placeItems: 'center',
          padding: 24,
          textAlign: 'center',
        }}>
        <div style={{ maxWidth: 420 }}>
          <h1 style={{ fontSize: 24, margin: '0 0 12px' }}>Доступ к приложению заблокирован</h1>
          <p style={{ fontSize: 14, lineHeight: 1.5, opacity: 0.95 }}>
            {profile.ban_app_reason || 'Если вы считаете это ошибкой — обратитесь лично.'}
          </p>
        </div>
      </div>
    )
  }

  if (!profile.consent_is_active) {
    return (
      <ConsentGateScreen
        deletionDueAt={profile.consent_deletion_due_at}
        busy={reconsentBusy}
        error={reconsentError}
        onAccept={() => void handleReconsent()}
        onShowPolicy={() => setShowPolicy(true)}
      />
    )
  }

  return (
    <>
      <Topbar />
      {platform.manifest.maintenance ? <MaintenanceNotice policy={platform.manifest.maintenance} /> : null}
      <Routes>
        <Route path='/' element={<HomePage />} />
        <Route path='/services' element={<ServicesPage />} />
        <Route path='/submissions' element={<SubmissionsPage />} />
        <Route path='/submit/:formId' element={<SubmitPage />} />
        <Route path='/tests/:testId' element={<TestPage />} />
        <Route path='/entrant' element={<Navigate to='/capabilities/admission_rating/lookup' replace />} />
        <Route path='/content/:slug' element={<ContentCategoryPage />} />
        <Route path='/capabilities/:capabilityKey/:viewKey' element={<CapabilityPage />} />

        <Route path='/monitoring' element={<Navigate to='/capabilities/request_status/lookup' replace />} />
        <Route path='/faq' element={<FaqPage />} />
        <Route path='/news' element={<NewsPage />} />
        <Route path='/profile' element={<ProfilePage onShowPolicy={() => setShowPolicy(true)} />} />
        <Route path='*' element={<Navigate to='/' replace />} />
      </Routes>
      <BottomNav />
    </>
  )
}
