import { useEffect } from 'react'
import { Navigate, useLocation, useParams } from 'react-router-dom'

import { useAuth } from '@/auth/AuthProvider'
import { trackAnalyticsEventInBackground } from '@/features/analytics/api/analyticsApi'
import { usePublishedContent } from '@/features/content/model/usePublishedContent'
import { BlockRendererRegistry } from '@/features/content/ui/renderers/BlockRendererRegistry'
import { usePlatform } from '@/features/platform-manifest/model/PlatformProvider'
import { getMissingProfileFields } from '@/features/profile-requirements/model/profileRequirements'

export function ContentCategoryPage() {
  const { slug } = useParams()
  const location = useLocation()
  const analyticsState = (location.state ?? {}) as {
    analyticsSource?: 'home' | 'category' | 'bottom_nav' | 'direct'
    sourceCategoryId?: number
  }
  const { content, loading, error } = usePublishedContent(slug)
  const { manifest } = usePlatform()
  const { profile } = useAuth()

  useEffect(() => {
    // A capability shortcut's own slug never gets this event -- it redirects below instead of
    // rendering as a page, and its taps from the category grid already report
    // capability_card_open (see useCapabilityLink).
    if (content && content.version_id !== null)
      trackAnalyticsEventInBackground({
        action_type: 'content_category_open',
        source_surface:
          analyticsState.analyticsSource ?? (content.parent_id === null ? 'direct' : 'category'),
        category_id: content.id,
        source_category_id: analyticsState.sourceCategoryId ?? content.parent_id ?? undefined,
        content_version_id: content.version_id,
      })
  }, [analyticsState.analyticsSource, analyticsState.sourceCategoryId, content])

  if (loading)
    return (
      <div className='screen'>
        <div className='skeleton' style={{ width: '62%', height: 28 }} />
        <div className='skeleton' style={{ width: '100%', height: 90, marginTop: 14 }} />
      </div>
    )

  // Direct navigation to a shortcut's own slug (typed by hand, a stale bookmark, or a link that
  // predates the shortcut being repointed) -- it has no content page to render, so redirect
  // straight to the capability view it points at, applying the same gating a tap on its grid
  // tile would (see CapabilityShortcutCard/useCapabilityLink).
  if (content && content.capability_key && content.capability_view_key) {
    const capability = manifest?.capabilities.find((item) => item.key === content.capability_key)
    const view = capability?.views.find((item) => item.key === content.capability_view_key)
    if (view?.requires_complete_profile) {
      const missing = getMissingProfileFields(profile, manifest?.bot.profile_schema)
      if (missing.length) return <Navigate to='/profile' replace />
    }
    if (view) return <Navigate to={view.path} replace />
    return (
      <div className='screen cms-page-error'>
        <h1 className='screen-title'>Страница недоступна</h1>
        <p>Сервис временно недоступен.</p>
      </div>
    )
  }

  if (error || !content)
    return (
      <div className='screen cms-page-error'>
        <h1 className='screen-title'>Страница недоступна</h1>
        <p>{error || 'Опубликованная версия не найдена.'}</p>
      </div>
    )
  return (
    <article className='screen cms-page'>
      <div className='cms-page__blocks'>
        {content.blocks.map((block) => (
          <BlockRendererRegistry key={block.id} block={block} content={content} />
        ))}
      </div>
    </article>
  )
}
