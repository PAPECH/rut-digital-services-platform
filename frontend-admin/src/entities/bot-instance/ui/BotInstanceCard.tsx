import { useState } from "react";

import type { BotInstance } from "@/api/types";
import { BotConfigurationFields } from "@/features/bot-instance-management/ui/BotConfigurationFields";
import { BotRuntimePanel } from "@/features/bot-runtime/ui/BotRuntimePanel";

type BotPatch = Partial<
  Pick<
    BotInstance,
    "name" | "description" | "is_active" | "order" | "branding" | "settings" | "profile_schema"
  >
>;

export function BotInstanceCard({
  bot,
  onUpdate,
  onOpen,
  onDelete,
  onRestore,
}: {
  bot: BotInstance;
  onUpdate: (botId: number, patch: BotPatch) => Promise<unknown>;
  onOpen: (bot: BotInstance) => void;
  onDelete: (botId: number) => Promise<unknown>;
  onRestore: (botId: number) => Promise<unknown>;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({
    name: bot.name,
    description: bot.description || "",
    order: bot.order,
    is_active: bot.is_active,
    branding: { ...bot.branding },
    settings: structuredClone(bot.settings),
    profile_schema: bot.profile_schema.map((field) => ({ ...field })),
  });

  const cancel = () => {
    setDraft({
      name: bot.name,
      description: bot.description || "",
      order: bot.order,
      is_active: bot.is_active,
      branding: { ...bot.branding },
      settings: structuredClone(bot.settings),
      profile_schema: bot.profile_schema.map((field) => ({ ...field })),
    });
    setEditing(false);
    setError(null);
  };

  if (bot.deleted_at) {
    return (
      <article className="card bot-instance-card bot-instance-card--deleted">
        <div className="card-body">
          <div className="bot-instance-card__head">
            <div>
              <h2 className="card-title">{bot.name}</h2>
              <code>{bot.slug}</code>
            </div>
            <span className="tag neutral">Удалён</span>
          </div>
          <p>{bot.description || "Описание не заполнено"}</p>
          <div className="content-inline-actions">
            <button
              className="btn btn-secondary btn-sm"
              disabled={restoring}
              onClick={() => {
                setRestoring(true);
                void onRestore(bot.id)
                  .catch((reason) => window.alert((reason as Error).message))
                  .finally(() => setRestoring(false));
              }}
            >
              {restoring ? "Восстановление…" : "Восстановить"}
            </button>
          </div>
        </div>
      </article>
    );
  }

  if (editing) {
    return (
      <article className="card bot-instance-card">
        <div className="card-body settings-form">
          <label>
            <span className="field-label">Название</span>
            <input
              className="input"
              value={draft.name}
              onChange={(event) =>
                setDraft((current) => ({ ...current, name: event.target.value }))
              }
            />
          </label>
          <label>
            <span className="field-label">Порядок</span>
            <input
              className="input"
              type="number"
              value={draft.order}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  order: Number(event.target.value) || 0,
                }))
              }
            />
          </label>
          <label className="settings-form__wide">
            <span className="field-label">Описание</span>
            <textarea
              className="textarea"
              rows={3}
              value={draft.description}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
            />
          </label>
          <label className="staff-permission settings-form__wide">
            <input
              type="checkbox"
              checked={draft.is_active}
              onChange={(event) =>
                setDraft((current) => ({
                  ...current,
                  is_active: event.target.checked,
                }))
              }
            />
            <span>Бот активен</span>
          </label>
          <BotConfigurationFields
            branding={draft.branding}
            fields={draft.profile_schema}
            onBrandingChange={(branding) =>
              setDraft((current) => ({ ...current, branding }))
            }
            onFieldsChange={(profile_schema) =>
              setDraft((current) => ({ ...current, profile_schema }))
            }
          />
          {error ? <p className="form-error settings-form__wide">{error}</p> : null}
          <div className="settings-form__actions">
            <code>{bot.slug}</code>
            <div className="content-inline-actions">
              <button className="btn btn-ghost" disabled={saving} onClick={cancel}>
                Отмена
              </button>
              <button
                className="btn btn-primary"
                disabled={saving || !draft.name.trim()}
                onClick={() => {
                  setSaving(true);
                  setError(null);
                  void onUpdate(bot.id, {
                    name: draft.name,
                    description: draft.description || null,
                    order: draft.order,
                    is_active: draft.is_active,
                    branding: draft.branding,
                    settings: draft.settings,
                    profile_schema: draft.profile_schema,
                  })
                    .then(() => setEditing(false))
                    .catch((reason) => setError((reason as Error).message))
                    .finally(() => setSaving(false));
                }}
              >
                {saving ? "Сохранение…" : "Сохранить"}
              </button>
            </div>
          </div>
        </div>
      </article>
    );
  }

  return (
    <article className="card bot-instance-card">
      <div className="card-body">
        <div className="bot-instance-card__head">
          <div>
            <h2 className="card-title">{bot.name}</h2>
            <code>{bot.slug}</code>
          </div>
          <span className={`tag ${bot.is_active ? "done" : "neutral"}`}>
            {bot.is_active ? "Активен" : "Выключен"}
          </span>
        </div>
        <p>{bot.description || "Описание не заполнено"}</p>
        <BotRuntimePanel botId={bot.id} botSlug={bot.slug} />
        <div className="content-inline-actions">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => onOpen(bot)}
          >
            Открыть в админке
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setEditing(true)}>
            Редактировать
          </button>
          <button
            className="btn btn-danger btn-sm"
            onClick={() => {
              if (
                window.confirm(
                  `Удалить бота «${bot.name}»? Он остановится и исчезнет из списка — восстановить можно в любой момент.`,
                )
              ) {
                void onDelete(bot.id).catch((reason) => window.alert((reason as Error).message));
              }
            }}
          >
            Удалить
          </button>
        </div>
      </div>
    </article>
  );
}
