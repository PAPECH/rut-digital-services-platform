import type { BotSettings } from '@/api/types'

function parseThreshold(value: string): number | null {
  if (!value.trim()) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

export function ChatKbSettingsEditor({
  settings,
  onChange,
}: {
  settings: BotSettings
  onChange: (settings: BotSettings) => void
}) {
  const chat = settings.chat ?? { student_text_enabled: true }
  const kb = settings.knowledge_base ?? {
    auto_answer_threshold: null,
    candidate_min_threshold: null,
    max_candidates: null,
  }

  return (
    <section className='chat-kb-settings'>
      <div>
        <span className='field-label'>Чат и поиск по базе знаний</span>
        <p className='profile-schema-editor__hint'>
          Настройка действует только для выбранного бота.
        </p>
      </div>

      <label style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginTop: 10 }}>
        <input
          type='checkbox'
          checked={chat.student_text_enabled}
          onChange={(e) =>
            onChange({
              ...settings,
              chat: { student_text_enabled: e.target.checked },
            })
          }
          style={{ marginTop: 3 }}
        />
        <span>
          <strong>Разрешить студентам писать боту текстом</strong>
          <br />
          <small style={{ color: 'var(--ink-400)' }}>
            Если выключено, бот игнорирует любой текст и всегда отвечает предложением
            открыть мини-приложение — как по /start. Поиск по базе знаний и очередь
            тикетов из текстовых сообщений для этого бота не работают.
          </small>
        </span>
      </label>

      <div style={{ marginTop: 16 }}>
        <span className='field-label'>Пороги релевантности базы знаний</span>
        <p className='profile-schema-editor__hint'>
          Пусто — используется платформенное значение по умолчанию. Проверить эффект
          изменений можно в разделе «База знаний» → «Тестовый режим».
        </p>
        <div className='submission-table-settings__grid' style={{ marginTop: 8 }}>
          <label className='field-label' style={{ fontWeight: 400 }}>
            Порог авто-ответа (0–1)
            <input
              className='input'
              type='number'
              min={0}
              max={1}
              step={0.01}
              value={kb.auto_answer_threshold ?? ''}
              placeholder='по умолчанию платформы'
              onChange={(e) =>
                onChange({
                  ...settings,
                  knowledge_base: { ...kb, auto_answer_threshold: parseThreshold(e.target.value) },
                })
              }
            />
          </label>
          <label className='field-label' style={{ fontWeight: 400 }}>
            Порог показа кандидатов (0–1)
            <input
              className='input'
              type='number'
              min={0}
              max={1}
              step={0.01}
              value={kb.candidate_min_threshold ?? ''}
              placeholder='по умолчанию платформы'
              onChange={(e) =>
                onChange({
                  ...settings,
                  knowledge_base: {
                    ...kb,
                    candidate_min_threshold: parseThreshold(e.target.value),
                  },
                })
              }
            />
          </label>
          <label className='field-label' style={{ fontWeight: 400 }}>
            Максимум кандидатов
            <input
              className='input'
              type='number'
              min={1}
              max={10}
              step={1}
              value={kb.max_candidates ?? ''}
              placeholder='по умолчанию платформы'
              onChange={(e) =>
                onChange({
                  ...settings,
                  knowledge_base: {
                    ...kb,
                    max_candidates: e.target.value.trim() ? Math.round(Number(e.target.value)) : null,
                  },
                })
              }
            />
          </label>
        </div>
      </div>
    </section>
  )
}
