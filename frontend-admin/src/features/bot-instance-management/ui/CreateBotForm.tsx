import { useState } from "react";

import type { CreateBotDraft } from "@/features/bot-instance-management/model/useBotInstances";
import { slugify } from "@/shared/lib/slugify";

const EMPTY_DRAFT: CreateBotDraft = { slug: "", name: "", description: "", botToken: "" };

export function CreateBotForm({
  creating,
  onCreate,
}: {
  creating: boolean;
  onCreate: (draft: CreateBotDraft) => Promise<unknown>;
}) {
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [slugTouched, setSlugTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    draft.slug.length >= 2 && !!draft.name.trim() && draft.botToken.trim().length >= 16;

  const reset = () => {
    setDraft(EMPTY_DRAFT);
    setSlugTouched(false);
  };

  return (
    <section className="card">
      <div className="card-head">
        <h2 className="card-title">Новый бот</h2>
      </div>
      <div className="card-body settings-form">
        <label>
          <span className="field-label">Название</span>
          <input
            className="input"
            value={draft.name}
            onChange={(event) => {
              const name = event.target.value;
              setDraft((current) => ({
                ...current,
                name,
                slug: slugTouched ? current.slug : slugify(name),
              }));
            }}
            placeholder="Кадровые сервисы"
          />
        </label>
        <label>
          <span className="field-label">Токен MAX-бота</span>
          <input
            className="input"
            type="password"
            autoComplete="new-password"
            value={draft.botToken}
            onChange={(event) =>
              setDraft((current) => ({ ...current, botToken: event.target.value }))
            }
            placeholder="Вставьте токен, выданный MAX"
          />
        </label>
        <label className="settings-form__wide">
          <span className="field-label">Описание (необязательно)</span>
          <textarea
            className="textarea"
            rows={2}
            value={draft.description}
            onChange={(event) =>
              setDraft((current) => ({
                ...current,
                description: event.target.value,
              }))
            }
          />
        </label>
        <details className="settings-form__wide">
          <summary className="muted">Технический адрес (slug): {draft.slug || "—"}</summary>
          <label>
            <span className="field-label">Slug</span>
            <input
              className="input"
              value={draft.slug}
              onChange={(event) => {
                setSlugTouched(true);
                setDraft((current) => ({
                  ...current,
                  slug: event.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, "-"),
                }));
              }}
              placeholder="hr-services"
            />
          </label>
        </details>
        {error ? <p className="form-error settings-form__wide">{error}</p> : null}
        <div className="settings-form__actions">
          <span className="muted">
            Бот запустится в фоне автоматически — ничего донастраивать не нужно.
          </span>
          <button
            className="btn btn-primary"
            disabled={creating || !canSubmit}
            onClick={() => {
              setError(null);
              void onCreate(draft)
                .then(() => reset())
                .catch((reason) => setError((reason as Error).message));
            }}
          >
            {creating ? "Создание…" : "Создать бота"}
          </button>
        </div>
      </div>
    </section>
  );
}
