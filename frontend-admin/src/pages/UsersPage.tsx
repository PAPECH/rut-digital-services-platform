import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, getCurrentAdminId } from '@/api/client'
import type { BotInstance, UserSummary } from '@/api/types'
import { Avatar } from '@/components/Avatar'
import { Icon } from '@/components/Icon'
import { UserCardPanel } from '@/components/UserCardPanel'
import { formatDateTime } from '@/lib/status'

function fullName(u: UserSummary): string {
  const parts = [u.last_name, u.first_name, u.patronymic].filter(Boolean) as string[]
  if (parts.length) return parts.join(' ')
  return u.username || u.user_id
}

function formatBirthDate(d: string | null): string {
  if (!d) return '—'
  try {
    return new Date(d).toLocaleDateString('ru-RU')
  } catch {
    return d
  }
}

export function UsersPage() {
  const navigate = useNavigate()
  const [users, setUsers] = useState<UserSummary[]>([])
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [showStudyGroup, setShowStudyGroup] = useState(false)
  const currentAdminId = getCurrentAdminId()

  const reload = useCallback(() => {
    const q = query ? `?query=${encodeURIComponent(query)}` : ''
    void api.get<UserSummary[]>(`/users${q}`).then(setUsers)
  }, [query])

  useEffect(() => {
    const id = setTimeout(reload, 200)
    return () => clearTimeout(id)
  }, [reload])

  useEffect(() => {
    // "Группа" — student-specific; only show the column for bots that actually
    // declare study_group in their profile schema (e.g. an HR bot shouldn't see it).
    void api.get<BotInstance>('/instances/current').then((bot) => {
      setShowStudyGroup(bot.profile_schema.some((field) => field.key === 'study_group'))
    })
  }, [])

  return (
    <div className='page'>
      <div className='page-head'>
        <div>
          <h1 className='page-title'>Пользователи</h1>
          <p className='page-sub'>Обратившиеся в бота</p>
        </div>
        <input
          className='input'
          style={{ maxWidth: 320 }}
          placeholder='Поиск по ФИО, MAX ID, телефону, группе…'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className='card'>
        <div style={{ overflowX: 'auto' }}>
          <table className='tbl'>
            <thead>
              <tr>
                <th>ФИО</th>
                <th>MAX ID</th>
                <th>Дата рождения</th>
                {showStudyGroup && <th>Группа</th>}
                <th>Создан</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => {
                const name = fullName(u)
                const banned = u.ban_app || u.ban_chat || u.ban_forms
                return (
                  <tr key={u.id} onClick={() => setSelectedId(u.id)} style={{ cursor: 'pointer' }}>
                    <td>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 10,
                        }}>
                        <Avatar size='sm' user={{ photo_url: u?.photo_url, fullName: name }} />
                        <div>
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 4,
                              fontWeight: 600,
                            }}>
                            <span>{name}</span>
                            {u.phone_verified && (
                              <span
                                title='Телефон подтверждён'
                                style={{
                                  color: 'var(--brand)',
                                  display: 'inline-flex',
                                  width: 14,
                                  height: 14,
                                }}>
                                <Icon.Check />
                              </span>
                            )}
                            {banned && (
                              <span
                                title={[
                                  u.ban_app ? 'приложение' : null,
                                  u.ban_chat ? 'чат' : null,
                                  u.ban_forms ? 'формы' : null,
                                ]
                                  .filter(Boolean)
                                  .join(', ')}
                                style={{
                                  background: 'var(--st-rej-bg)',
                                  color: 'var(--st-rej-fg)',
                                  fontSize: 10,
                                  padding: '1px 6px',
                                  borderRadius: 10,
                                  fontWeight: 700,
                                }}>
                                BAN
                              </span>
                            )}
                          </div>
                          {u.username && (
                            <div
                              style={{
                                fontSize: 11.5,
                                color: 'var(--ink-400)',
                              }}>
                              @{u.username}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className='mono'>{u.user_id}</td>
                    <td>{formatBirthDate(u.birth_date)}</td>
                    {showStudyGroup && <td>{u.study_group ?? <span className='muted'>—</span>}</td>}
                    <td className='num'>{formatDateTime(u.created_at)}</td>
                  </tr>
                )
              })}
              {users.length === 0 && (
                <tr>
                  <td
                    colSpan={showStudyGroup ? 5 : 4}
                    style={{
                      textAlign: 'center',
                      padding: 32,
                      color: 'var(--ink-400)',
                    }}>
                    Пользователей нет
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {selectedId != null && (
        <UserCardPanel
          userId={selectedId}
          currentAdminId={currentAdminId}
          onClose={() => setSelectedId(null)}
          onOpenTickets={(userId) => navigate(`/tickets?user=${userId}`)}
        />
      )}
    </div>
  )
}
