import { useEffect } from 'react'

import { useAuth } from '@/auth/AuthProvider'
import { useI18n } from '@/i18n'
import { renderTemplate } from '@/lib/renderTemplate'
import { trackAnalyticsEventInBackground } from '@/features/analytics/api/analyticsApi'
import { ContentCategoryGrid } from '@/features/content/ui/ContentCategoryGrid'
import { useHomeContent } from '@/features/content/model/HomeContentProvider'
import { BlockRendererRegistry } from '@/features/content/ui/renderers/BlockRendererRegistry'
import { usePlatform } from '@/features/platform-manifest/model/PlatformProvider'

export function HomePage() {
  const { profile } = useAuth()
  const { t } = useI18n()
  const platform = usePlatform()
  const { content, loading, error } = useHomeContent()
  const greeting = profile?.first_name
    ? `${t('home:main:greet')}, ${profile.first_name}!`
    : `${t('home:main:greeting')}!`

  useEffect(() => {
    if (content)
      trackAnalyticsEventInBackground({
        action_type: 'content_category_open',
        source_surface: 'direct',
        category_id: content.id,
        // Non-null: the home screen is never a capability shortcut (is_home is unreachable from
        // the shortcut-creation path).
        content_version_id: content.version_id as number,
      })
  }, [content])

  if (loading) {
    return (
      <div className='screen'>
        <div className='skeleton' style={{ width: '62%', height: 28 }} />
        <div className='skeleton' style={{ width: '100%', height: 90, marginTop: 14 }} />
      </div>
    )
  }

  // Resilient fallback: never leave the app's landing screen blank if the home-content read
  // fails -- fall back to the pre-CMS static layout (greeting + top-level category grid).
  if (error || !content) {
    return (
      <div className='screen'>
        <h1 className='screen-title'>{greeting}</h1>
        <p className='screen-sub'>{t('home:main:subtitle', { name: platform.manifest?.bot.name ?? '' })}</p>
        <ContentCategoryGrid />
      </div>
    )
  }

  return (
    <article className='screen cms-page'>
      {content.header_visible ? (
        <>
          <h1 className='screen-title'>{renderTemplate(content.title, { profile })}</h1>
          {content.subtitle ? (
            <p className='screen-sub'>{renderTemplate(content.subtitle, { profile })}</p>
          ) : null}
        </>
      ) : null}
      <div className='cms-page__blocks'>
        {content.blocks.map((block) => (
          <BlockRendererRegistry key={block.id} block={block} content={content} />
        ))}
      </div>
    </article>
  )
}
