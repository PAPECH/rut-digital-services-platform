import { useMemo, useState } from "react";

import { EntityDropdownPicker } from "@/components/EntityDropdownPicker";
import { CreateFormForm } from "@/features/form-management/ui/CreateFormForm";
import { FormDraftEditor } from "@/features/form-management/ui/FormDraftEditor";
import { SharedFormDraftPicker } from "@/features/form-management/ui/SharedFormDraftPicker";
import { useFormBuilder } from "@/features/form-management/model/useFormBuilder";

export function BuilderPage() {
  const builder = useFormBuilder();
  const [creating, setCreating] = useState(false);
  const [sharedDraftsOpen, setSharedDraftsOpen] = useState(false);
  const dirty = useMemo(
    () =>
      Boolean(
        builder.draft &&
        builder.active &&
        JSON.stringify(builder.draft) !== JSON.stringify(builder.active.draft),
      ),
    [builder.draft, builder.active],
  );
  const canPublish = Boolean(
    builder.active &&
    builder.draft &&
    !dirty &&
    builder.draft.revision > builder.active.last_published_revision,
  );
  return (
    <div className="page content-builder-page form-builder-page">
      <div className="page-head content-builder-head">
        <div>
          <h1 className="page-title">Конструктор форм</h1>
          <p className="page-sub">
            Компактное редактирование типизированных полей, черновиков и версий.
          </p>
        </div>
        <div className="content-head-actions">
          <EntityDropdownPicker
            items={builder.forms.map((form) => ({
              id: form.id,
              title: form.draft.name,
              subtitle: form.slug,
              badge: {
                text: form.is_archived ? "архив" : form.is_active ? "видна" : "скрыта",
                tone: !form.is_archived && form.is_active ? "success" : "neutral",
              },
            }))}
            activeId={builder.active?.id ?? null}
            reordering={builder.busy === "reorder"}
            placeholder="Выберите форму"
            emptyLabel="Форм пока нет"
            onSelect={(id) => {
              const form = builder.forms.find((item) => item.id === id);
              if (form) builder.select(form);
            }}
            onMove={(id, direction) => void builder.move(id, direction)}
          />
          <button
            className="btn btn-secondary"
            type="button"
            onClick={() => setSharedDraftsOpen(true)}
          >
            Общие черновики
          </button>
          <button
            className="btn btn-primary"
            type="button"
            onClick={() => setCreating(true)}
          >
            Новая форма
          </button>
        </div>
      </div>
      {sharedDraftsOpen ? (
        <SharedFormDraftPicker
          existingSlugs={builder.forms.map((form) => form.slug)}
          onImport={async (sourceFormId, slug) => {
            await builder.importSharedDraft(sourceFormId, slug);
          }}
          onClose={() => setSharedDraftsOpen(false)}
        />
      ) : null}
      {creating ? (
        <CreateFormForm
          order={builder.forms.length}
          onCreate={builder.create}
          onCancel={() => setCreating(false)}
        />
      ) : null}
      {builder.error ? (
        <div className="content-status content-status--error">
          <span>{builder.error}</span>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => void builder.reload()}
          >
            Обновить
          </button>
        </div>
      ) : null}
      {builder.notice ? (
        <div className="content-status content-status--success">
          {builder.notice}
        </div>
      ) : null}
      <div className="content-builder-layout form-builder-layout">
        <section className="card content-builder-editor">
          {builder.loading ? (
            <div className="content-empty-state content-empty-state--large">
              <strong>Загрузка…</strong>
            </div>
          ) : !builder.active || !builder.draft ? (
            <div className="content-empty-state content-empty-state--large">
              <strong>Выберите форму</strong>
              <span>Здесь появятся её поля и параметры.</span>
            </div>
          ) : (
            <>
              <div className="card-head content-builder-toolbar">
                <div>
                  <h2 className="card-title">
                    {builder.draft.name || "Без названия"}
                  </h2>
                  <p className="card-sub">
                    Черновик · ревизия {builder.draft.revision}
                  </p>
                </div>
                <div className="content-toolbar-actions">
                  <label className="content-checkbox">
                    <input
                      type="checkbox"
                      checked={builder.active.is_active}
                      disabled={
                        builder.active.is_archived ||
                        !builder.active.published_version_id ||
                        builder.busy !== null
                      }
                      onChange={(e) =>
                        void builder.patch({ is_active: e.target.checked })
                      }
                    />
                    Показывать
                  </label>
                  <label className="content-checkbox">
                    <input
                      type="checkbox"
                      checked={builder.active.show_in_catalog}
                      disabled={builder.active.is_archived || builder.busy !== null}
                      onChange={(event) =>
                        void builder.patch({ show_in_catalog: event.target.checked })
                      }
                    />
                    В общем каталоге
                  </label>
                  <label className="content-checkbox" title="Другие администраторы смогут скопировать этот черновик в свой бот">
                    <input
                      type="checkbox"
                      checked={builder.draft.is_shared}
                      disabled={builder.busy !== null}
                      onChange={(event) =>
                        builder.setDraft({
                          ...builder.draft!,
                          is_shared: event.target.checked,
                        })
                      }
                    />
                    Общий черновик
                  </label>
                  <button
                    className="btn btn-secondary"
                    type="button"
                    disabled={!dirty || builder.busy !== null}
                    onClick={() => void builder.save()}
                  >
                    {builder.busy === "save" ? "Сохранение…" : "Сохранить"}
                  </button>
                  <button
                    className="btn btn-primary"
                    type="button"
                    disabled={!canPublish || builder.busy !== null}
                    onClick={() => {
                      if (window.confirm("Опубликовать сохранённую ревизию?"))
                        void builder.publish();
                    }}
                  >
                    {builder.busy === "publish"
                      ? "Публикация…"
                      : "Опубликовать"}
                  </button>
                  {builder.active.is_archived ? (
                    <button
                      className="btn btn-secondary"
                      type="button"
                      disabled={builder.busy !== null}
                      onClick={() => void builder.patch({ is_archived: false })}
                    >
                      Восстановить
                    </button>
                  ) : (
                    <button
                      className="btn btn-danger"
                      type="button"
                      disabled={builder.busy !== null}
                      onClick={() => {
                        if (
                          window.confirm(
                            "Архивировать форму? Заявки и версии сохранятся.",
                          )
                        )
                          void builder.patch({ is_archived: true });
                      }}
                    >
                      В архив
                    </button>
                  )}
                </div>
              </div>
              {dirty ? (
                <div className="content-unsaved">
                  Есть несохранённые изменения.
                </div>
              ) : null}
              {builder.active.is_archived ? (
                <div className="content-unpublished">
                  Форма находится в архиве и недоступна пользователям.
                </div>
              ) : null}
              {!builder.active.published_version_id ? (
                <div className="content-unpublished">
                  Форма ещё не публиковалась и недоступна пользователям.
                </div>
              ) : null}
              <div className="card-body">
                <FormDraftEditor
                  draft={builder.draft}
                  onChange={builder.setDraft}
                />
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
