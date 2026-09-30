import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, getCurrentAdminId, getToken } from '@/api/client'
import { createAdminWebSocketUrl } from '@/api/config'
import { getSelectedBotSlug } from '@/shared/tenant/selectedBotStorage'
import type {
  BotInstance,
  ProfileFieldDefinition,
  StatusHistoryItem,
  Submission,
  SubmissionStatus,
} from '@/api/types'
import type { AdminForm, FormField } from '@/entities/form/model/types'

import { StatusTag } from '@/components/StatusTag'
import { EntityDropdownPicker } from '@/components/EntityDropdownPicker'
import { UserCardPanel } from '@/components/UserCardPanel'
import { useSubmissionAttachments } from '@/features/submission-attachments/model/useSubmissionAttachments'
import { submissionFileFieldKeys } from '@/features/submission-attachments/model/submissionFileFields'
import { SubmissionAttachmentList } from '@/features/submission-attachments/ui/SubmissionAttachmentList'
import { submissionTableProfileColumns } from '@/features/submission-profile/model/submissionProfile'
import { SubmissionProfileSummary } from '@/features/submission-profile/ui/SubmissionProfileSummary'
import { AppointmentScheduler } from '@/features/submission-appointments/ui/AppointmentScheduler'
import { useSubmissionsViewMode } from '@/features/submission-table/model/useSubmissionsViewMode'
import { SubmissionsTable } from '@/features/submission-table/ui/SubmissionsTable'
import { DEFAULT_SUBMISSION_PROFILE_FIELD_KEYS } from '@/entities/profile/model/profileDisplayFields'
import { formatDateTime, statusLabel } from '@/lib/status'
import { notify } from '@/lib/notify'

const STATUSES: SubmissionStatus[] = ['new', 'in_work', 'done', 'rejected']
const LIMITS: number[] = [10, 25, 50, 100, -1]

export function SubmissionsPage() {
  const [forms, setForms] = useState<AdminForm[]>([])
  const [activeForm, setActiveForm] = useState<AdminForm | null>(null)
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [statusFilter, setStatusFilter] = useState<SubmissionStatus | 'all'>('all')
  const [fieldFilters, setFieldFilters] = useState<Record<string, string>>({})
  const [selected, setSelected] = useState<Submission | null>(null)
  const [openUserId, setOpenUserId] = useState<number | null>(null)
  const [profileSchema, setProfileSchema] = useState<ProfileFieldDefinition[]>([])
  const [profileFieldKeys, setProfileFieldKeys] = useState<string[]>([
    ...DEFAULT_SUBMISSION_PROFILE_FIELD_KEYS,
  ])

  const [limit, setLimit] = useState<number>(
    localStorage.getItem('submissions_limit') ? Number(localStorage.getItem('submissions_limit')) : 100,
  )

  const [loading, setLoading] = useState(false)
  const currentAdminId = getCurrentAdminId()
  const { viewMode, setViewMode } = useSubmissionsViewMode()

  useEffect(() => {
    void api.get<AdminForm[]>('/forms/admin').then((rows) => {
      setForms(rows)
      if (rows.length) {
        setActiveForm(rows[0])
      }
    })
  }, [])

  useEffect(() => {
    void api.get<BotInstance>('/instances/current').then((bot) => {
      setProfileSchema(bot.profile_schema)
      setProfileFieldKeys(
        bot.settings.submission_table?.profile_fields ?? [...DEFAULT_SUBMISSION_PROFILE_FIELD_KEYS],
      )
    })
  }, [])

  useEffect(() => {
    localStorage.setItem('submissions_limit', String(limit))
  }, [limit])

  const loadForm = useCallback(
    async (formId: number) => {
      const selected = forms.find((form) => form.id === formId)
      if (selected) setActiveForm(selected)
    },
    [forms],
  )

  const reload = useCallback(async () => {
    if (!activeForm) return
    setLoading(true)
    const params = new URLSearchParams()
    params.set('form_id', String(activeForm.id))
    params.set('limit', String(limit))
    if (statusFilter !== 'all') params.set('status', statusFilter)
    for (const [k, v] of Object.entries(fieldFilters)) {
      if (v) params.set(k, v)
    }
    try {
      const rows = await api.get<Submission[]>(`/submissions?${params.toString()}`)
      setSubmissions(rows)
    } finally {
      setLoading(false)
    }
  }, [activeForm, statusFilter, fieldFilters, limit])

  useEffect(() => {
    void reload()
  }, [reload])

  const changeStatus = async (sub: Submission, status: SubmissionStatus) => {
    if (activeForm?.slug === 'form-priem' && status === 'done' && !sub.appointment) {
      window.alert('Сначала откройте заявку и назначьте дату и время встречи.')
      return
    }
    let comment: string | undefined = undefined
    if (status === 'rejected') {
      const result = window.prompt('Комментарий к отклонению (необязательно)')
      if (result === null) return
      comment = result || undefined
    }
    const updated = await api.patch<Submission>(`/submissions/${sub.id}/status`, { status, comment })

    setSubmissions((rows) => rows.map((r) => (r.id === sub.id ? { ...r, ...updated } : r)))
    if (selected?.id === sub.id) setSelected({ ...selected, ...updated })
  }

  const openCard = async (sub: Submission) => {
    const fresh = await api.get<Submission>(`/submissions/${sub.id}`)
    setSelected(fresh)
  }

  const wsRef = useRef<WebSocket | null>(null)
  useEffect(() => {
    const token = getToken()
    if (!token) return
    const url = createAdminWebSocketUrl('/ws/chat')
    url.searchParams.set('token', token)
    url.searchParams.set('bot_slug', getSelectedBotSlug())
    const ws = new WebSocket(url.toString())
    wsRef.current = ws
    ws.onmessage = (e) => {
      try {
        const ev = JSON.parse(e.data)
        if (ev.type === 'new_submission') {
          const fresh = ev.data as Submission
          if (activeForm && fresh.form_template_id === activeForm.id) {
            if (statusFilter === 'all' || statusFilter === fresh.status) {
              setSubmissions((prev) => {
                if (prev.some((p) => p.id === fresh.id)) return prev
                return [fresh, ...prev]
              })
            }
          }
          const who = fresh.submitter
            ? `${fresh.submitter.last_name ?? ''} ${fresh.submitter.first_name ?? ''}`.trim()
            : ''
          notify('Новая заявка', `${fresh.form_name ?? 'Заявка'} от ${who}`)
        }
        if (ev.type === 'submission_updated') {
          const fresh = ev.data as Submission
          setSubmissions((rows) => rows.map((r) => (r.id === fresh.id ? { ...r, ...fresh } : r)))
        }
        if (ev.type === 'forms_changed') {
          void api.get<AdminForm[]>('/forms/admin').then((rows) => {
            setForms(rows)
            if (activeForm) setActiveForm(rows.find((form) => form.id === activeForm.id) ?? null)
          })
        }
      } catch {}
    }
    return () => ws.close()
  }, [activeForm, statusFilter, loadForm])

  const fieldsForFilter = activeForm?.draft.fields ?? []
  const activeFields: FormField[] = useMemo(
    () => (activeForm?.draft.fields ?? []).filter((f) => f.active),
    [activeForm],
  )
  const tableFields: FormField[] = useMemo(
    () => (viewMode === 'wide' ? activeFields : activeFields.slice(0, 4)),
    [activeFields, viewMode],
  )
  const filterFields = useMemo(() => {
    const eligible = fieldsForFilter.filter((f) =>
      ['short_text', 'long_text', 'email', 'phone', 'select', 'radio'].includes(f.type),
    )
    return viewMode === 'wide' ? eligible : eligible.slice(0, 4)
  }, [fieldsForFilter, viewMode])
  const profileColumns = useMemo(
    () => submissionTableProfileColumns(profileSchema, profileFieldKeys),
    [profileFieldKeys, profileSchema],
  )

  return (
    <div className='page'>
      <div className='submissions-layout'>
        <div className='submissions-layout__main'>
          <div className='card' style={{ marginBottom: 16 }}>
            <div className='card-body' style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              <EntityDropdownPicker
                items={forms.map((f) => ({
                  id: f.id,
                  title: f.draft.name,
                  badge: f.is_active ? undefined : { text: 'скрыта', tone: 'neutral' },
                }))}
                activeId={activeForm?.id ?? null}
                placeholder='Выберите форму'
                emptyLabel='Форм пока нет'
                onSelect={loadForm}
              />

              <div className='pill-tabs'>
                <button
                  className={statusFilter === 'all' ? 'active' : ''}
                  onClick={() => setStatusFilter('all')}>
                  Все
                </button>
                {STATUSES.map((s) => (
                  <button
                    key={s}
                    className={statusFilter === s ? 'active' : ''}
                    onClick={() => setStatusFilter(s)}>
                    {statusLabel(s)}
                  </button>
                ))}
              </div>

              {filterFields.map((f) => (
                <input
                  key={f.key}
                  className='input'
                  style={{ maxWidth: 200 }}
                  placeholder={`${f.label}…`}
                  value={fieldFilters[`f_${f.key}`] ?? ''}
                  onChange={(e) =>
                    setFieldFilters((prev) => ({
                      ...prev,
                      [`f_${f.key}`]: e.target.value,
                    }))
                  }
                />
              ))}
              <select
                className='input'
                style={{ maxWidth: 200 }}
                onChange={(e) => setLimit(Number(e.target.value))}
                value={limit}>
                {LIMITS.map((l) => (
                  <option key={l} value={l}>
                    {l === -1 ? 'Показывать все' : `Лимит: ${l}`}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className='card'>
            <div className='card-head'>
              <h3 className='card-title'>Заявки</h3>
              <div className='pill-tabs' role='group' aria-label='Отображение таблицы'>
                <button className={viewMode === 'compact' ? 'active' : ''} onClick={() => setViewMode('compact')}>
                  Кратко
                </button>
                <button className={viewMode === 'wide' ? 'active' : ''} onClick={() => setViewMode('wide')}>
                  Все поля
                </button>
              </div>
            </div>
            <SubmissionsTable
              profileColumns={profileColumns}
              tableFields={tableFields}
              submissions={submissions}
              loading={loading}
              onOpenUser={setOpenUserId}
              onOpenCard={(s) => void openCard(s)}
              onChangeStatus={changeStatus}
            />
          </div>
        </div>
      </div>

      {selected && (
        <SubmissionDrawer
          submission={selected}
          form={activeForm}
          profileSchema={profileSchema}
          onClose={() => setSelected(null)}
          onOpenUser={(id) => {
            setSelected(null)
            setOpenUserId(id)
          }}
          onAppointmentBooked={(updated) => {
            setSelected(updated)
            setSubmissions((rows) => rows.map((row) => (row.id === updated.id ? updated : row)))
          }}
        />
      )}

      {openUserId != null && (
        <UserCardPanel
          userId={openUserId}
          currentAdminId={currentAdminId}
          onClose={() => setOpenUserId(null)}
        />
      )}
    </div>
  )
}

function renderValue(v: unknown): React.ReactNode {
  if (v === null || v === undefined || v === '') return <span className='muted'>—</span>
  if (typeof v === 'boolean') return v ? 'Да' : 'Нет'
  if (Array.isArray(v)) {
    if (!v.length) return <span className='muted'>—</span>
    return v.map(String).join(', ')
  }
  return String(v)
}

function SubmissionDrawer({
  submission,
  form,
  profileSchema,
  onClose,
  onOpenUser,
  onAppointmentBooked,
}: {
  submission: Submission
  form: AdminForm | null
  profileSchema: ProfileFieldDefinition[]
  onClose: () => void
  onOpenUser: (id: number) => void
  onAppointmentBooked: (updated: Submission) => void
}) {
  const attachments = useSubmissionAttachments(submission.id)
  const fileFieldKeys = useMemo(
    () => submissionFileFieldKeys(submission.form_snapshot, form?.draft.fields ?? []),
    [form?.draft.fields, submission.form_snapshot],
  )
  const labelFor = useMemo(() => {
    const snapshot = submission.field_labels ?? {}
    const byCurrentForm = Object.fromEntries((form?.draft.fields ?? []).map((f) => [f.key, f.label]))
    return (fid: string): string => snapshot[fid] ?? byCurrentForm[fid] ?? `Поле ${fid}`
  }, [submission.field_labels, form])

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        display: 'flex',
        justifyContent: 'flex-end',
      }}>
      <div
        onClick={onClose}
        style={{
          position: 'absolute',
          inset: 0,
          background: 'rgba(11,23,41,.32)',
        }}
      />
      <div
        style={{
          position: 'relative',
          width: 520,
          maxWidth: '100vw',
          height: '100%',
          background: '#fff',
          borderLeft: '1px solid var(--line)',
          boxShadow: 'var(--shadow-lg)',
          display: 'flex',
          flexDirection: 'column',
        }}>
        <div
          style={{
            padding: '18px 22px',
            borderBottom: '1px solid var(--line)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700 }}>Заявка #{submission.id}</div>
            <div style={{ fontSize: 12.5, color: 'var(--ink-400)' }}>{submission.form_name ?? ''}</div>
          </div>
          <button className='btn btn-ghost btn-icon' onClick={onClose}>
            ×
          </button>
        </div>
        <div style={{ padding: '16px 22px', overflow: 'auto' }}>
          <SubmissionProfileSummary
            submission={submission}
            profileSchema={profileSchema}
            onOpenUser={submission.submitter ? () => onOpenUser(submission.submitter!.id) : null}
          />

          <div style={{ marginBottom: 16 }}>
            <StatusTag status={submission.status} />
            <div style={{ fontSize: 12.5, color: 'var(--ink-400)', marginTop: 8 }}>
              Создана: {formatDateTime(submission.created_at)}
            </div>
          </div>

          <h4
            style={{
              fontSize: 12,
              color: 'var(--ink-500)',
              textTransform: 'uppercase',
              letterSpacing: '.06em',
            }}>
            Данные формы
          </h4>
          <div style={{ display: 'grid', gap: 8, marginTop: 8 }}>
            {Object.entries(submission.values).map(([fid, val]) => {
              const fieldAttachments = attachments.byField.get(fid) ?? []
              const isFileField = fileFieldKeys.has(fid)
              return (
                <div
                  key={fid}
                  className={isFileField ? 'submission-field submission-field--files' : 'submission-field'}>
                  <span className='submission-field__label'>{labelFor(fid)}</span>
                  {fieldAttachments.length ? (
                    <SubmissionAttachmentList items={fieldAttachments} />
                  ) : isFileField && attachments.loading ? (
                    <span className='submission-attachments__state'>Загружаем файл…</span>
                  ) : isFileField ? (
                    <span className='submission-attachments__state submission-attachments__state--error'>
                      Файл недоступен
                    </span>
                  ) : (
                    <span className='submission-field__value'>{renderValue(val)}</span>
                  )}
                </div>
              )
            })}
            {attachments.loading ? (
              <div className='submission-attachments__state'>Загружаем прикреплённые файлы…</div>
            ) : null}
            {attachments.error ? (
              <div className='submission-attachments__state submission-attachments__state--error'>
                {attachments.error}
              </div>
            ) : null}
          </div>

          {form?.slug === 'form-priem' ? (
            submission.appointment ? (
              <section className='appointment-summary'>
                <span className='appointment-summary__eyebrow'>Встреча назначена</span>
                <strong>
                  {new Intl.DateTimeFormat('ru-RU', {
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric',
                    timeZone: 'Europe/Moscow',
                  }).format(new Date(submission.appointment.starts_at))}
                  {', '}
                  {new Intl.DateTimeFormat('ru-RU', {
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZone: 'Europe/Moscow',
                  }).format(new Date(submission.appointment.starts_at))}
                  {'–'}
                  {new Intl.DateTimeFormat('ru-RU', {
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZone: 'Europe/Moscow',
                  }).format(new Date(submission.appointment.ends_at))}
                </strong>
                <span>{submission.appointment.location}</span>
                <small>Продолжительность: {submission.appointment.duration_minutes} минут</small>
              </section>
            ) : submission.status === 'in_work' ? (
              <AppointmentScheduler submission={submission} onBooked={onAppointmentBooked} />
            ) : submission.status === 'new' ? (
              <p className='appointment-scheduler__hint'>
                Переведите заявку в статус «В работе», чтобы назначить дату и время встречи.
              </p>
            ) : null
          ) : null}

          <h4
            style={{
              fontSize: 12,
              color: 'var(--ink-500)',
              textTransform: 'uppercase',
              letterSpacing: '.06em',
              marginTop: 22,
            }}>
            История статусов
          </h4>
          <div style={{ marginTop: 8 }}>
            {(submission.history ?? []).map((h: StatusHistoryItem) => (
              <div
                key={h.id}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: '8px 0',
                  borderBottom: '1px solid var(--line)',
                  fontSize: 13,
                }}>
                <div>
                  {h.from_status ? `${statusLabel(h.from_status)} → ` : ''}
                  <b>{statusLabel(h.to_status)}</b>
                  {h.comment && <div style={{ color: 'var(--ink-400)', fontSize: 12 }}>{h.comment}</div>}
                </div>
                <span style={{ color: 'var(--ink-400)' }}>{formatDateTime(h.changed_at)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
