import type { AdminProfile } from '@/api/types'
import { Avatar } from '@/components/Avatar'
import { Icon } from '@/components/Icon'

export function AdminAccount({
  admin,
  language,
  roleLabel,
  logoutLabel,
  onToggleLanguage,
  onLogout,
}: {
  admin: AdminProfile
  language: 'ru' | 'en'
  roleLabel: string
  logoutLabel: string
  onToggleLanguage: () => void
  onLogout: () => void
}) {
  return (
    <div className='nav-right'>
      <button className='icon-btn' title={logoutLabel} onClick={onLogout}>
        <span className='ico'>
          <Icon.Logout />
        </span>
      </button>
      <div className='me'>
        <Avatar user={{ fullName: admin.full_name }} />
        <div className='who'>
          <b>{shortName(admin.full_name)}</b>
          <span>{roleLabel}</span>
        </div>
      </div>
    </div>
  )
}

function shortName(fullName: string): string {
  const parts = fullName.trim().split(/\s+/)
  if (parts.length < 2) return fullName
  return `${parts[0][0]}. ${parts[1]}`
}
