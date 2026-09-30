import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Icon } from '@/components/Icon'
import type { BlockRendererProps, TestActionBlock } from '@/entities/content/model/types'
import { trackAnalyticsEventInBackground } from '@/features/analytics/api/analyticsApi'
import { useIsPreviewMode } from '@/features/content/model/PreviewModeContext'

export function TestActionBlockRenderer({ block, content }: BlockRendererProps<TestActionBlock>) {
  const navigate = useNavigate()
  const isPreview = useIsPreviewMode()
  const [message, setMessage] = useState<string | null>(null)

  const openTest = () => {
    if (isPreview) {
      setMessage('Прохождение тестов недоступно в предпросмотре')
      return
    }

    trackAnalyticsEventInBackground({
      action_type: 'content_block_interaction',
      interaction_kind: 'test_card_open',
      source_surface: 'category',
      category_id: content.id,
      content_version_id: content.version_id,
      block_id: block.id,
    })
    navigate(`/tests/${block.test_id}`)
  }
  return (
    <div>
      <button type='button' className='card service-form-card cms-form-action' onClick={openTest}>
        <span>
          <strong>{block.title ?? block.description ?? 'Пройти тест'}</strong>
          {block.title && block.description ? <small>{block.description}</small> : null}
        </span>
        <span className='ico' aria-hidden='true'>
          <Icon.ChevronRight />
        </span>
      </button>
      {message ? <div className='cms-form-action__warning'>{message}</div> : null}
    </div>
  )
}
