import { useEffect, useState } from 'react'
import { api } from '@/api/client'
import type { BotInstance, BotSettings } from '@/api/types'
import { useI18n } from '@/i18n'
import { MaintenancePanel } from '@/features/maintenance/ui/MaintenancePanel'
import { BottomNavigationEditor } from '@/features/bot-instance-management/ui/BottomNavigationEditor'
import { SubmissionTableFieldsEditor } from '@/features/bot-instance-management/ui/SubmissionTableFieldsEditor'
import { ChatKbSettingsEditor } from '@/features/bot-instance-management/ui/ChatKbSettingsEditor'
import { contentApi } from '@/features/content-management/api/contentApi'
import type { AdminContentCategory } from '@/entities/content/model/types'

interface SettingOut {
  key: string
  value: string | null
}

const KEYS = ['bot_start_message_ru', 'bot_start_message_en'] as const

export function BotSettingsPage() {
  const { t } = useI18n()
  const [values, setValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState<string | null>(null)
  const [savedAt, setSavedAt] = useState<string | null>(null)
  const [navigation, setNavigation] = useState<BotSettings | null>(null)
  const [persistedSettings, setPersistedSettings] = useState<BotSettings | null>(null)
  const [profileSchema, setProfileSchema] = useState<BotInstance['profile_schema']>([])
  const [categories, setCategories] = useState<AdminContentCategory[]>([])
  const [savingNavigation, setSavingNavigation] = useState(false)
  const [savingSubmissionTable, setSavingSubmissionTable] = useState(false)
  const [savingChatKb, setSavingChatKb] = useState(false)
  const [navigationError, setNavigationError] = useState<string | null>(null)
  const [submissionTableError, setSubmissionTableError] = useState<string | null>(null)
  const [chatKbError, setChatKbError] = useState<string | null>(null)

  useEffect(() => {
    void Promise.all(KEYS.map((k) => api.get<SettingOut>(`/settings/${k}`))).then((rows) => {
      const v: Record<string, string> = {}
      for (const r of rows) v[r.key] = r.value ?? ''
      setValues(v)
    })
  }, [])

  useEffect(() => {
    void Promise.all([api.get<BotInstance>('/instances/current'), contentApi.list()])
      .then(([bot, availableCategories]) => {
        setNavigation(bot.settings)
        setPersistedSettings(bot.settings)
        setProfileSchema(bot.profile_schema)
        setCategories(
          availableCategories.filter((category) => category.is_active && category.published_version_id),
        )
      })
      .catch((reason: unknown) => {
        setNavigationError(
          reason instanceof Error ? reason.message : 'Не удалось загрузить настройки интерфейса',
        )
      })
  }, [])

  const save = async (key: string) => {
    setSaving(key)
    try {
      await api.put(`/settings/${key}`, { value: values[key] || null })
      setSavedAt(new Date().toLocaleTimeString())
    } finally {
      setSaving(null)
    }
  }

  const saveNavigation = async () => {
    if (!navigation || !persistedSettings) return
    if (
      navigation.bottom_navigation.custom_items.some(
        (item) => !item.label.trim() || ((item.target ?? 'category') === 'category' && !item.category_slug),
      )
    ) {
      setNavigationError('Выберите экран и заполните подпись каждого пункта.')
      return
    }
    setSavingNavigation(true)
    setNavigationError(null)
    try {
      const payload: BotSettings = {
        ...persistedSettings,
        bottom_navigation: navigation.bottom_navigation,
        profile: navigation.profile,
      }
      const bot = await api.patch<BotInstance>('/instances/current/settings', payload)
      setPersistedSettings(bot.settings)
      setNavigation((current) =>
        current ? { ...bot.settings, submission_table: current.submission_table } : bot.settings,
      )
    } catch (reason) {
      setNavigationError(
        reason instanceof Error ? reason.message : 'Не удалось сохранить настройки интерфейса',
      )
    } finally {
      setSavingNavigation(false)
    }
  }

  const saveSubmissionTable = async () => {
    if (!navigation || !persistedSettings) return
    setSavingSubmissionTable(true)
    setSubmissionTableError(null)
    try {
      const payload: BotSettings = {
        ...persistedSettings,
        submission_table: navigation.submission_table,
      }
      const bot = await api.patch<BotInstance>('/instances/current/settings', payload)
      setPersistedSettings(bot.settings)
      setNavigation((current) =>
        current
          ? { ...bot.settings, bottom_navigation: current.bottom_navigation, profile: current.profile }
          : bot.settings,
      )
    } catch (reason) {
      setSubmissionTableError(
        reason instanceof Error ? reason.message : 'Не удалось сохранить поля таблицы заявок',
      )
    } finally {
      setSavingSubmissionTable(false)
    }
  }

  const saveChatKb = async () => {
    if (!navigation || !persistedSettings) return
    const kb = navigation.knowledge_base
    if (
      kb.auto_answer_threshold != null &&
      kb.candidate_min_threshold != null &&
      kb.candidate_min_threshold > kb.auto_answer_threshold
    ) {
      setChatKbError('Порог показа кандидатов не может быть больше порога авто-ответа.')
      return
    }
    setSavingChatKb(true)
    setChatKbError(null)
    try {
      const payload: BotSettings = {
        ...persistedSettings,
        chat: navigation.chat,
        knowledge_base: navigation.knowledge_base,
      }
      const bot = await api.patch<BotInstance>('/instances/current/settings', payload)
      setPersistedSettings(bot.settings)
      setNavigation((current) =>
        current
          ? {
              ...bot.settings,
              bottom_navigation: current.bottom_navigation,
              submission_table: current.submission_table,
              profile: current.profile,
            }
          : bot.settings,
      )
    } catch (reason) {
      setChatKbError(
        reason instanceof Error ? reason.message : 'Не удалось сохранить настройки чата',
      )
    } finally {
      setSavingChatKb(false)
    }
  }

  return (
    <div className='page'>
      <div className='page-head'>
        <div>
          <h1 className='page-title'>{t('page.bot_settings.title')}</h1>
          <p className='page-sub'>{t('page.bot_settings.sub')}</p>
        </div>
      </div>

      <div className='grid responsive-two-column'>
        {KEYS.map((key) => (
          <div key={key} className='card'>
            <div className='card-head'>
              <h3 className='card-title'>
                {key === 'bot_start_message_ru' ? 'Текст /start (RU)' : '/start message (EN)'}
              </h3>
              <p className='card-sub'>{key}</p>
            </div>
            <div className='card-body'>
              <textarea
                className='textarea'
                style={{ minHeight: 180, resize: 'vertical' }}
                value={values[key] ?? ''}
                onChange={(e) => setValues((prev) => ({ ...prev, [key]: e.target.value }))}
                placeholder={
                  key === 'bot_start_message_ru'
                    ? 'Привет! Это бот РУТ МИИТ…'
                    : 'Hello! This is the RUT MIIT bot…'
                }
              />
              <div
                style={{
                  marginTop: 12,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}>
                <span style={{ fontSize: 12, color: 'var(--ink-400)' }}>
                  {savedAt ? `Сохранено в ${savedAt}` : 'Изменения применятся к следующему /start'}
                </span>
                <button className='btn btn-primary' disabled={saving === key} onClick={() => void save(key)}>
                  {saving === key ? t('common.loading') : t('action.save')}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className='card' style={{ marginTop: 16 }}>
        <div className='card-head'>
          <div>
            <h3 className='card-title'>Интерфейс бота</h3>
            <p className='card-sub'>Меню mini-app и отображение заявок для выбранного бота.</p>
          </div>
        </div>
        <div className='card-body'>
          {navigation ? (
            <>
              <BottomNavigationEditor
                settings={navigation}
                categories={categories}
                profileSchema={profileSchema}
                onChange={setNavigation}
              />
              {navigationError ? <p className='form-error'>{navigationError}</p> : null}
              <div className='content-form-actions'>
                <button
                  type='button'
                  className='btn btn-primary'
                  disabled={savingNavigation || savingSubmissionTable}
                  onClick={() => void saveNavigation()}>
                  {savingNavigation ? 'Сохранение…' : 'Сохранить нижнее меню'}
                </button>
              </div>
            </>
          ) : (
            <p className={navigationError ? 'form-error' : 'muted'}>{navigationError ?? 'Загрузка…'}</p>
          )}
          {navigation ? (
            <>
              <div className='settings-section-divider' />
              <SubmissionTableFieldsEditor
                settings={navigation}
                profileSchema={profileSchema}
                onChange={setNavigation}
              />
              {submissionTableError ? <p className='form-error'>{submissionTableError}</p> : null}
              <div className='content-form-actions'>
                <button
                  type='button'
                  className='btn btn-primary'
                  disabled={savingNavigation || savingSubmissionTable}
                  onClick={() => void saveSubmissionTable()}>
                  {savingSubmissionTable ? 'Сохранение…' : 'Сохранить поля таблицы'}
                </button>
              </div>
            </>
          ) : null}
        </div>
      </div>
      <div className='card' style={{ marginTop: 16 }}>
        <div className='card-head'>
          <div>
            <h3 className='card-title'>Чат и база знаний</h3>
            <p className='card-sub'>Приём текстовых сообщений и релевантность поиска.</p>
          </div>
        </div>
        <div className='card-body'>
          {navigation ? (
            <>
              <ChatKbSettingsEditor settings={navigation} onChange={setNavigation} />
              {chatKbError ? <p className='form-error'>{chatKbError}</p> : null}
              <div className='content-form-actions'>
                <button
                  type='button'
                  className='btn btn-primary'
                  disabled={savingNavigation || savingSubmissionTable || savingChatKb}
                  onClick={() => void saveChatKb()}>
                  {savingChatKb ? 'Сохранение…' : 'Сохранить настройки чата'}
                </button>
              </div>
            </>
          ) : (
            <p className={navigationError ? 'form-error' : 'muted'}>{navigationError ?? 'Загрузка…'}</p>
          )}
        </div>
      </div>
      <div style={{ marginTop: 16 }}>
        <MaintenancePanel scope='current' title='Технический режим этого бота' />
      </div>
    </div>
  )
}
