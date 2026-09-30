import { useCallback, useEffect, useRef, useState } from 'react'
import { api, getCurrentAdminId, getToken } from '@/api/client'
import { createAdminWebSocketUrl, resolveAdminAssetUrl } from '@/api/config'
import { getSelectedBotSlug } from '@/shared/tenant/selectedBotStorage'
import { KB_STAFF_REQUESTED_MARKER, type ConversationItem, type MessageItem } from '@/api/types'
import { Avatar } from '@/components/Avatar'
import { Icon } from '@/components/Icon'
import { UserCardPanel } from '@/components/UserCardPanel'
import { TicketConversationHeader } from '@/entities/ticket/ui/TicketConversationHeader'
import { useTicketSearch } from '@/features/ticket-search/model/useTicketSearch'
import { TicketSearchInput } from '@/features/ticket-search/ui/TicketSearchInput'
import { formatDateTime } from '@/lib/status'
import { type UploadedFile, formatBytes, isImageMime, uploadFile } from '@/api/files'
import {
  disableNotify,
  isNotifyEnabled,
  isNotifySupported,
  notify,
  requestNotifyPermission,
} from '@/lib/notify'
import { useI18n } from '@/i18n'
import { useContextMenu } from '@/hook/useContextMenu'
import ContextMenu from '../components/ContextMenu/ContextMenu'

import { useAuth } from '@/auth/AuthProvider'

const TICKET_LIMITS: number[] = [10, 25, 50, 100, 200]

export function TicketsPage() {
  const { admin } = useAuth()
  const ticketSearch = useTicketSearch()
  const { query, requestedUserId } = ticketSearch

  const [convs, setConvs] = useState<ConversationItem[]>([])
  const [onlyOpen, setOnlyOpen] = useState(false)
  const [isOnlyFreeTicket, setIsOnlyFreeTicket] = useState(!requestedUserId)
  const [limit, setLimit] = useState<number>(
    localStorage.getItem('tickets_limit') ? Number(localStorage.getItem('tickets_limit')) : 50,
  )
  const [activeUser, setActiveUser] = useState<ConversationItem | null>(null)
  const [profileUserId, setProfileUserId] = useState<number | null>(null)
  const [messages, setMessages] = useState<MessageItem[]>([])
  const [convAdmins, setConvAdmins] = useState<string[] | null>(null)
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [pending, setPending] = useState<UploadedFile[]>([])
  const [uploading, setUploading] = useState(false)

  const { contextMenu, menuRef, openMenu, closeMenu } = useContextMenu()

  const wsRef = useRef<WebSocket | null>(null)
  const messagesRef = useRef<HTMLDivElement | null>(null)
  const bottomRef = useRef<HTMLDivElement | null>(null)

  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [notifyOn, setNotifyOn] = useState<boolean>(() => isNotifyEnabled())
  const { t } = useI18n()
  const currentAdminId = getCurrentAdminId()

  const reloadConvs = useCallback(() => {
    const params = new URLSearchParams({
      only_open: String(onlyOpen),
      only_free: String(isOnlyFreeTicket),
      limit: String(limit),
    })
    if (query.trim()) params.set('query', query.trim())
    if (requestedUserId && !query.trim()) {
      params.set('user_id', String(requestedUserId))
    }
    api
      .get<ConversationItem[]>(`/tickets/conversations?${params.toString()}`)
      .then((data) => {
        const sorted = [...data].sort((a, b) => {
          if (a.my_favorite === b.my_favorite) return 0
          return a.my_favorite ? -1 : 1
        })
        setConvs(sorted)
      })
      .catch(() => setConvs([]))
  }, [onlyOpen, isOnlyFreeTicket, limit, query, requestedUserId])

  useEffect(() => {
    localStorage.setItem('tickets_limit', String(limit))
  }, [limit])

  useEffect(() => {
    const timeout = window.setTimeout(reloadConvs, 200)
    return () => window.clearTimeout(timeout)
  }, [reloadConvs])

  useEffect(() => {
    if (!requestedUserId) return
    const requested = convs.find((conversation) => conversation.user_id === requestedUserId)
    if (requested) {
      setActiveUser(requested)
      ticketSearch.consumeRequestedUser()
    }
  }, [convs, requestedUserId])

  const selectConversation = (conversation: ConversationItem) => {
    setActiveUser(conversation)
  }

  const changeQuery = (value: string) => {
    setIsOnlyFreeTicket(false)
    ticketSearch.setQuery(value)
  }

  useEffect(() => {
    const token = getToken()
    if (!token) return
    const url = createAdminWebSocketUrl('/ws/chat')
    url.searchParams.set('token', token)
    url.searchParams.set('bot_slug', getSelectedBotSlug())
    if (activeUser) url.searchParams.set('user_pk', String(activeUser.user_id))
    const ws = new WebSocket(url.toString())
    wsRef.current = ws

    ws.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data)
        console.log('Received message:', ev)

        if (ev.type === 'message' && activeUser && ev.data.user_id === activeUser.user_id) {
          setMessages((prev) => {
            if (prev.some((m) => m.id === ev.data.id)) return prev
            return [...prev, ev.data]
          })
        }
        if (ev.type === 'new_ticket') {
          reloadConvs()
          const text = ev?.data?.text ?? ''
          notify(t('push.title'), text)
        }
        if (ev.type === 'ticket_answered') {
          reloadConvs()
        }
      } catch {}
    }
    return () => ws.close()
  }, [activeUser, reloadConvs, currentAdminId, t])

  useEffect(() => {
    if (!activeUser) {
      setMessages([])
      return
    }
    api
      .get<MessageItem[]>(`/messages?user_id=${activeUser.user_id}`)
      .then(setMessages)
      .catch(() => setMessages([]))

    api
      .get<string[]>(`/tickets/admins?user_id=${activeUser.user_id}`)
      .then(setConvAdmins)
      .catch(() => setConvAdmins(null))
  }, [activeUser])

  useEffect(() => {
    setTimeout(() => {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, 0)
  }, [messages])

  const send = async () => {
    if (!activeUser) return
    const trimmed = text.trim()
    if (!trimmed && pending.length === 0) return
    setSending(true)
    try {
      await api.post<MessageItem>(`/messages/to-user/${activeUser.user_id}`, {
        text: trimmed || null,
        attachment_ids: pending.map((p) => p.id),
      })
      // setMessages((prev) => [...prev, msg]);
      setText('')
      setPending([])
      reloadConvs()
    } finally {
      setSending(false)
    }
  }

  const onPickFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return
    setUploading(true)
    try {
      const uploaded = await uploadFile(f)
      setPending((prev) => [...prev, uploaded])
    } catch (err) {
      alert((err as Error).message)
    } finally {
      setUploading(false)
    }
  }
  const colorConvHandler = (e: ConversationItem) => {
    if (e.my_favorite) {
      return 'var(--st-work-bg)'
    } else if (e.is_favorite) {
      return 'var(--st-new-bg)'
    } else {
      return 'transparent'
    }
  }
  return (
    <div className='page' style={{ overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      <div className='page-head'>
        <div>
          <h1 className='page-title'>{t('page.tickets.title')}</h1>
          <p className='page-sub'>{t('page.tickets.sub')}</p>
        </div>

        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <TicketSearchInput value={query} onChange={changeQuery} />
          {isNotifySupported() && (
            <button
              className={`btn btn-sm ${notifyOn ? 'btn-secondary' : 'btn-primary'}`}
              onClick={async () => {
                if (notifyOn) {
                  disableNotify()
                  setNotifyOn(false)
                } else {
                  const ok = await requestNotifyPermission()
                  setNotifyOn(ok)
                }
              }}>
              <span className='ico' style={{ width: 14, height: 14 }}>
                <Icon.Bell />
              </span>
              {notifyOn ? t('push.disable') : t('push.enable')}
            </button>
          )}

          <div className='pill-tabs' style={{ gap: 12 }}>
            <button className={isOnlyFreeTicket ? 'active' : ''} onClick={() => setIsOnlyFreeTicket(true)}>
              Только свободные тикеты
            </button>
            <button className={!isOnlyFreeTicket ? 'active' : ''} onClick={() => setIsOnlyFreeTicket(false)}>
              Все
            </button>
          </div>

          <div className='pill-tabs'>
            <button className={onlyOpen ? 'active' : ''} onClick={() => setOnlyOpen(true)}>
              Без ответа
            </button>
            <button className={!onlyOpen ? 'active' : ''} onClick={() => setOnlyOpen(false)}>
              Все
            </button>
          </div>

          <select
            className='input'
            style={{ maxWidth: 160 }}
            onChange={(e) => setLimit(Number(e.target.value))}
            value={limit}>
            {TICKET_LIMITS.map((l) => (
              <option key={l} value={l}>
                {`Лимит: ${l}`}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div
        style={{
          gap: 12,
          alignItems: 'center',
          justifyContent: 'right',
          display: 'flex',
          flexWrap: 'wrap',
        }}>
        {convAdmins && convAdmins.length > 0 && (
          <div className='page-sub' style={{ margin: '0 0 12px 0' }}>
            Закреплено за:{' '}
            {convAdmins.map((name, index) => (
              <span className={`tag ${name == admin?.full_name ? 'done' : 'outline'}`} key={index}>
                {name == admin?.full_name ? 'Вами' : name}
              </span>
            ))}
          </div>
        )}
      </div>
      <div
        className='grid'
        style={{
          gridTemplateColumns: '320px 1fr',
          height: 'calc(100vh - 200px)',
        }}>
        <div className='card' style={{ overflow: 'auto' }}>
          {convs.map((c) => {
            const name = `${c.last_name ?? ''} ${c.first_name ?? ''}`.trim() || c.username || '—'
            const active = activeUser?.user_id === c.user_id
            return (
              <div
                key={c.user_id}
                onClick={() => selectConversation(c)}
                onMouseEnter={(e) => (e.currentTarget.style.background = '#f0f0f0')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                onContextMenu={(e) => openMenu(e, c.user_id, c.my_favorite, c.has_open_ticket)}
                style={{
                  display: 'flex',
                  gap: 10,
                  padding: '10px 5px',
                  borderBottom: '1px solid var(--line)',
                  borderLeft: `10px solid ${colorConvHandler(c)}`,
                  cursor: 'pointer',
                  background: active ? 'var(--brand-50)' : undefined,
                }}>
                <Avatar user={{ photo_url: c?.photo_url, fullName: name }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: 8,
                    }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{name}</div>
                    <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                      {c.staff_requested && (
                        <span
                          title='Студент явно запросил сотрудника'
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: 3,
                            background: 'var(--st-work-bg)',
                            color: 'var(--st-work-fg)',
                            fontSize: 10.5,
                            padding: '2px 6px',
                            borderRadius: 10,
                            fontWeight: 700,
                          }}>
                          <span className='ico' style={{ width: 10, height: 10 }}>
                            <Icon.User />
                          </span>
                          Человек
                        </span>
                      )}
                      {c.has_open_ticket && (
                        <span
                          style={{
                            background: 'var(--st-rej-bg)',
                            color: 'var(--st-rej-fg)',
                            fontSize: 10.5,
                            padding: '2px 6px',
                            borderRadius: 10,
                            fontWeight: 700,
                          }}>
                          НОВ
                        </span>
                      )}
                    </div>
                  </div>
                  <div className='ticket-max-id'>MAX ID: {c.max_user_id}</div>
                  <div
                    style={{
                      fontSize: 12,
                      color: 'var(--ink-400)',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                    {c.last_message_text || '—'}
                  </div>
                  <div
                    style={{
                      fontSize: 10.5,
                      color: 'var(--ink-300)',
                      marginTop: 2,
                    }}>
                    {c.last_message_at ? formatDateTime(c.last_message_at) : ''}
                  </div>
                </div>
              </div>
            )
          })}
          {contextMenu && (
            <ContextMenu
              menuRef={menuRef}
              position={{ x: contextMenu.x, y: contextMenu.y }}
              row_id={contextMenu.itemId}
              isFavorite={contextMenu.isFavorite}
              isOpen={contextMenu.isOpen}
              closeMenu={closeMenu}
              setConvs={setConvs}
            />
          )}

          {convs.length === 0 && (
            <div
              style={{
                padding: 32,
                textAlign: 'center',
                color: 'var(--ink-400)',
              }}>
              Нет обращений
            </div>
          )}
        </div>

        <div className='card' style={{ display: 'flex', flexDirection: 'column', overflow: 'auto' }}>
          {!activeUser ? (
            <div
              style={{
                flex: 1,
                display: 'grid',
                placeItems: 'center',
                color: 'var(--ink-400)',
              }}>
              Выберите обращение слева
            </div>
          ) : (
            <>
              <TicketConversationHeader
                conversation={activeUser}
                onOpenProfile={() => setProfileUserId(activeUser.user_id)}
              />
              <div
                ref={messagesRef}
                style={{
                  flex: 1,
                  overflow: 'auto',
                  padding: 20,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                }}>
                {messages.map((m) =>
                  m.ai_classification === KB_STAFF_REQUESTED_MARKER ? (
                    <SystemEventLine key={m.id} msg={m} />
                  ) : (
                    <ChatBubble key={m.id} msg={m} currentAdminId={currentAdminId} />
                  ),
                )}
                <div ref={bottomRef} />
              </div>
              <div
                style={{
                  padding: 16,
                  borderTop: '1px solid var(--line)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}>
                {pending.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {pending.map((p) => (
                      <span key={p.id} className='tag outline' style={{ paddingRight: 4 }}>
                        {p.name} · {formatBytes(p.size_bytes)}
                        <button
                          onClick={() => setPending((prev) => prev.filter((x) => x.id !== p.id))}
                          style={{
                            background: 'transparent',
                            border: 0,
                            cursor: 'pointer',
                            marginLeft: 4,
                            color: 'var(--ink-400)',
                          }}
                          title='Убрать вложение'>
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
                <div style={{ display: 'flex', gap: 8 }}>
                  <input ref={fileInputRef} type='file' hidden onChange={(e) => void onPickFile(e)} />
                  <button
                    className='btn btn-secondary btn-icon'
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    title='Прикрепить файл'>
                    <span className='ico'>
                      <Icon.Paperclip />
                    </span>
                  </button>
                  <textarea
                    className='textarea'
                    rows={1}
                    placeholder='Сообщение студенту…'
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        void send()
                      }
                    }}
                    style={{ resize: 'none' }}
                  />
                  <button
                    className='btn btn-primary'
                    disabled={sending || (!text.trim() && pending.length === 0)}
                    onClick={() => void send()}>
                    Отправить
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
      {profileUserId !== null ? (
        <UserCardPanel
          userId={profileUserId}
          currentAdminId={currentAdminId}
          onClose={() => setProfileUserId(null)}
          onOpenTickets={(userId) => {
            setProfileUserId(null)
            const conversation = convs.find((item) => item.user_id === userId)
            if (conversation) selectConversation(conversation)
          }}
        />
      ) : null}
    </div>
  )
}

/** Синтетическое системное событие (например «студент запросил сотрудника» через
 * кнопку «Позвать сотрудника»), а не текст, который кто-то реально напечатал —
 * рендерится отдельно от обычных пузырей чата, чтобы оператор не принял его за
 * настоящее сообщение студента. */
function SystemEventLine({ msg }: { msg: MessageItem }) {
  return (
    <div
      style={{
        alignSelf: 'center',
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        maxWidth: '85%',
        background: 'var(--ink-100)',
        color: 'var(--ink-500)',
        padding: '6px 12px',
        borderRadius: 999,
        fontSize: 11.5,
        textAlign: 'center',
      }}>
      <span className='ico' style={{ width: 12, height: 12, flexShrink: 0 }}>
        <Icon.User />
      </span>
      <span>Студент запросил сотрудника</span>
      <span style={{ opacity: 0.7 }}>· {formatDateTime(msg.created_at)}</span>
    </div>
  )
}

function ChatBubble({ msg, currentAdminId }: { msg: MessageItem; currentAdminId: number | null }) {
  const isOut = msg.direction === 'out'
  const attachments = msg.attachments ?? []
  const authorLabel =
    isOut && msg.replied_by_admin_name
      ? msg.replied_by_admin_id === currentAdminId
        ? `${msg.replied_by_admin_name} (вы)`
        : msg.replied_by_admin_name
      : null
  return (
    <div
      style={{
        alignSelf: isOut ? 'flex-end' : 'flex-start',
        maxWidth: '75%',
        background: isOut ? 'var(--brand)' : 'var(--ink-50)',
        color: isOut ? '#fff' : 'var(--ink-900)',
        padding: '10px 14px',
        borderRadius: 12,
        fontSize: 13,
        lineHeight: 1.4,
      }}>
      {authorLabel && (
        <div
          style={{
            fontSize: 11.5,
            fontWeight: 700,
            marginBottom: 4,
            opacity: 0.9,
          }}>
          {authorLabel}
        </div>
      )}
      {msg.text && <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>}

      {attachments.length > 0 && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
            marginTop: msg.text ? 8 : 0,
          }}>
          {attachments.map((a, i) =>
            isImageMime(a.mime) ? (
              <a key={i} href={resolveAdminAssetUrl(a.url)} target='_blank' rel='noopener noreferrer'>
                <img
                  src={resolveAdminAssetUrl(a.url)}
                  alt={a.name ?? ''}
                  style={{
                    maxWidth: 240,
                    maxHeight: 240,
                    borderRadius: 8,
                    display: 'block',
                  }}
                />
              </a>
            ) : (
              <a
                key={i}
                href={resolveAdminAssetUrl(a.url)}
                download={a.name ?? 'file'}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '6px 10px',
                  borderRadius: 8,
                  background: isOut ? 'rgba(255,255,255,.15)' : '#fff',
                  color: isOut ? '#fff' : 'var(--ink-900)',
                  textDecoration: 'none',
                  fontSize: 12.5,
                }}>
                <span className='ico' style={{ width: 14, height: 14 }}>
                  <Icon.Download />
                </span>
                <span>{a.name ?? 'файл'}</span>
                {a.size ? <span style={{ opacity: 0.6 }}>· {formatBytes(a.size)}</span> : null}
              </a>
            ),
          )}
        </div>
      )}

      {msg.is_ai_answered && !isOut && (
        <div style={{ fontSize: 10.5, opacity: 0.6, marginTop: 4 }}>авто-ответ</div>
      )}
      <div style={{ fontSize: 10.5, marginTop: 4, opacity: 0.6 }}>{formatDateTime(msg.created_at)}</div>
    </div>
  )
}
