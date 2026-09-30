import { Link } from 'react-router-dom'

import type { PublishedCategorySummary } from '@/entities/content/model/types'
import { ContentIcon } from '@/entities/content/ui/ContentIcon'
import { useCapabilityLink } from '@/features/capabilities/model/useCapabilityLink'
import { useContentCategories } from '@/features/content/model/useContentCategories'
import { useCachedImageSrc } from '@/lib/useCachedImageSrc'

/** Split out so the `useCachedImageSrc` hook can be called once per card, inside the `.map()`
 * below, without violating the rules of hooks. Falls back to the raw `imageUrl` while the
 * in-memory cache hasn't resolved it yet (rare in practice -- the catalog-wide warmup in
 * ContentCatalogProvider/HomeContentProvider means it's almost always already cached by the time
 * a card actually mounts). */
function CategoryCardIcon({ icon, imageUrl }: { icon: string; imageUrl: string | null }) {
  const cachedSrc = useCachedImageSrc(imageUrl)
  if (imageUrl == null) return <ContentIcon name={icon} />
  return <img src={cachedSrc ?? imageUrl} alt='' />
}

/** A capability shortcut tile (Task 044): looks and is styled identically to an ordinary
 * category card, but resolves its destination through the platform manifest and applies the
 * same install-state/profile-completeness gating a `capability_action` content block already
 * applies, instead of linking to `/content/{slug}` -- a shortcut has no content page to render. */
function CapabilityShortcutCard({ category }: { category: PublishedCategorySummary }) {
  const { view, message, handleClick, navigateToProfile } = useCapabilityLink({
    capabilityKey: category.capability_key as string,
    viewKey: category.capability_view_key as string,
    categoryId: category.id,
    contentVersionId: null,
    blockId: `category-${category.id}`,
  })
  return (
    <>
      <Link
        className={`cms-category-card ${category.is_filled ? 'cms-category-card--filled' : ''}`}
        to={view?.path ?? '#'}
        aria-disabled={!view}
        onClick={handleClick}>
        <span className='cms-category-text'>
          <strong>{category.title}</strong>
          {category.subtitle ? <small>{category.subtitle}</small> : null}
        </span>
        <span className='cms-category-card__icon' aria-hidden='true'>
          <CategoryCardIcon icon={category.icon} imageUrl={category.image_url} />
        </span>
      </Link>
      {message ? (
        <div className='cms-form-action__warning'>
          {message}
          {view?.requires_complete_profile ? (
            <button type='button' onClick={navigateToProfile}>
              Перейти в профиль
            </button>
          ) : null}
        </div>
      ) : null}
    </>
  )
}

export function ContentCategoryGrid({
  parentId = null,
  title = parentId === null ? 'Полезная информация' : 'Разделы',
}: {
  parentId?: number | null
  title?: string
}) {
  const { categories, loading, error, reload } = useContentCategories()
  if (loading)
    return (
      <div className='cms-category-loading'>
        <span className='skeleton' />
        <span className='skeleton' />
      </div>
    )
  if (error)
    return (
      <div className='cms-load-error'>
        <span>{error}</span>
        <button type='button' onClick={() => void reload()}>
          Повторить
        </button>
      </div>
    )
  const visibleCategories = categories.filter((category) => category.parent_id === parentId)
  if (!visibleCategories.length) return null
  return (
    <section className='cms-category-section'>
      <div className='cms-category-grid'>
        {visibleCategories.map((category) =>
          category.capability_key && category.capability_view_key ? (
            <CapabilityShortcutCard category={category} key={category.id} />
          ) : (
            <Link
              className={`cms-category-card ${category.is_filled ? 'cms-category-card--filled' : ''}`}
              key={category.id}
              to={`/content/${category.slug}`}
              state={{
                analyticsSource: parentId === null ? 'home' : 'category',
                sourceCategoryId: parentId ?? undefined,
              }}>
              <span className='cms-category-text'>
                <strong>{category.title}</strong>
                {category.subtitle ? <small>{category.subtitle}</small> : null}
              </span>
              <span className='cms-category-card__icon' aria-hidden='true'>
                <CategoryCardIcon icon={category.icon} imageUrl={category.image_url} />
              </span>
            </Link>
          ),
        )}
      </div>
    </section>
  )
}
