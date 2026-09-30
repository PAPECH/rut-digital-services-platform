import { useState } from 'react'

import type { AccordionBlock, BlockRendererProps } from '@/entities/content/model/types'
import { Icon } from '@/components/Icon'
import { trackAnalyticsEventInBackground } from '@/features/analytics/api/analyticsApi'

export function AccordionBlockRenderer({ block, content }: BlockRendererProps<AccordionBlock>) {
  const [openIds, setOpenIds] = useState<Set<string>>(new Set())

  const toggle = (itemId: string) => {
    const isOpen = openIds.has(itemId)

    if (!isOpen) {
      trackAnalyticsEventInBackground({
        action_type: 'content_block_interaction',
        interaction_kind: 'accordion_item_open',
        source_surface: 'category',
        category_id: content.id,
        content_version_id: content.version_id,
        block_id: block.id,
        item_id: itemId,
      })
    }

    setOpenIds((prev) => {
      const next = new Set(prev)
      if (isOpen) {
        next.delete(itemId)
      } else {
        next.add(itemId)
      }
      return next
    })
  }

  return (
    <div className='faq-list-block'>
      {block.items.map((item) => {
        const open = openIds.has(item.id)
        const answerId = `accordion-answer-${item.id}`

        return (
          <div key={item.id} className='faq-item'>
            <button
              type='button'
              className='faq-q'
              aria-expanded={open}
              aria-controls={answerId}
              onClick={() => toggle(item.id)}>
              <span>{item.title}</span>
              <span
                className='ico'
                aria-hidden='true'
                style={{
                  width: 18,
                  height: 18,
                  color: 'var(--ink-400)',
                  transform: open ? 'rotate(180deg)' : 'none',
                  transition: 'transform .15s',
                }}>
                <Icon.ChevronDown />
              </span>
            </button>
            {open ? (
              <div id={answerId} className='faq-a'>
                {item.text}
              </div>
            ) : null}
          </div>
        )
      })}
    </div>
  )
}
