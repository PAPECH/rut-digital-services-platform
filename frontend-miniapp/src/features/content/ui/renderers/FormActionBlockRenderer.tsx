import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/AuthProvider'
import { Icon } from '@/components/Icon'
import type { BlockRendererProps, FormActionBlock } from '@/entities/content/model/types'
import { trackAnalyticsEventInBackground } from '@/features/analytics/api/analyticsApi'
import { useIsPreviewMode } from '@/features/content/model/PreviewModeContext'
import { useI18n } from '@/i18n'

export function FormActionBlockRenderer({ block, content }: BlockRendererProps<FormActionBlock>) {
  const navigate = useNavigate()
  const { profile } = useAuth()
  const isPreview = useIsPreviewMode()
  const [message, setMessage] = useState<string | null>(null)
  const banned = profile?.ban_forms ?? false

  const { t } = useI18n()

  const openForm = () => {
    if (isPreview) {
      setMessage('Отправка форм недоступна в предпросмотре')
      return
    }
    if (banned) {
      setMessage(profile?.ban_forms_reason || 'Отправка форм недоступна')
      return
    }

    trackAnalyticsEventInBackground({
      action_type: 'content_block_interaction',
      interaction_kind: 'form_card_open',
      source_surface: 'category',
      category_id: content.id,
      content_version_id: content.version_id,
      block_id: block.id,
      form_template_id: block.form_id,
    })
    navigate(`/submit/${block.form_id}`, {
      state: {
        analyticsSource: 'category',
        categoryId: content.id,
        contentVersionId: content.version_id,
        blockId: block.id,
      },
    })
  }
  return (
    <div>
      <button type='button' className='card service-form-card cms-form-action' onClick={openForm}>
        <span>
          <strong>{block.title ?? block.description ?? 'Открыть форму'}</strong>
          {block.title && block.description ? <small>{block.description}</small> : null}
        </span>
        <span className='ico' aria-hidden='true'>
          <Icon.ChevronRight />
        </span>
      </button>
      {message ? (
        <div className='cms-form-action__warning'>
          {message}
          {!isPreview ? (
            <button type='button' onClick={() => navigate('/profile')}>
              {t('services:main:to_profile')}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
