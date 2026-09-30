import { initials } from '@/lib/status'

import { useState } from 'react'

interface AvatarUser {
  photo_url?: string | null
  fullName: string
}

interface Props {
  user: AvatarUser
  size?: 'sm' | 'md' | 'lg'
  bg?: string
  className?: string
}

export function Avatar({ user, size = 'md', bg, className }: Props) {
  const [imgFailed, setImgFailed] = useState(false)
  const sizeCls = size === 'sm' ? 'sm' : size === 'lg' ? 'lg' : ''

  const style: React.CSSProperties | undefined = bg
    ? {
        background: bg,
        color: '#fff',
        boxShadow: 'inset 0 0 0 2px rgba(255,255,255,.18)',
      }
    : undefined

  const cls = `avatar ${sizeCls} ${className ?? ''}`.trim()

  if (user.photo_url && !imgFailed) {
    return (
      <div className={cls} style={style}>
        <img
          src={user.photo_url}
          alt={user.fullName}
          className='avatar-img'
          height={'32px'}
          width={'32px'}
          onError={() => setImgFailed(true)}
        />
      </div>
    )
  }

  return (
    <div className={cls} style={style}>
      {initials(user.fullName)}
    </div>
  )
}
