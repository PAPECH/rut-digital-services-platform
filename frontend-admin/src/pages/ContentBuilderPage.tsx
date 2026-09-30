import { useMemo, useState } from "react";

import { isShortcutCategory } from "@/entities/content/model/types";
import { ContentIcon } from "@/entities/content/ui/ContentIcon";
import { CapabilityShortcutForm } from "@/features/content-management/ui/CapabilityShortcutForm";
import { CategoryList } from "@/features/content-management/ui/CategoryList";
import { ContentDraftEditor } from "@/features/content-management/ui/ContentDraftEditor";
import { CreateCategoryForm } from "@/features/content-management/ui/CreateCategoryForm";
import { SharedContentDraftPicker } from "@/features/content-management/ui/SharedContentDraftPicker";
import { ContentPreviewFrame } from "@/features/content-management/ui/preview/ContentPreviewFrame";
import { useContentBuilder } from "@/features/content-management/model/useContentBuilder";
import { ContentEditorResourcesProvider } from "@/features/content-management/model/ContentEditorResourcesContext";

type MobilePanel = "categories" | "editor" | "preview";

export function ContentBuilderPage() {
  const builder = useContentBuilder();
  const [creatingParentId, setCreatingParentId] = useState<number | null | undefined>(undefined);
  const [creatingShortcutParentId, setCreatingShortcutParentId] = useState<number | null | undefined>(
    undefined,
  );
  const [sharedDraftsOpen, setSharedDraftsOpen] = useState(false);
  const [mobilePanel, setMobilePanel] = useState<MobilePanel>("categories");
  const dirty = useMemo(
    () =>
      Boolean(
        builder.draft &&
        builder.active &&
        JSON.stringify(builder.draft) !== JSON.stringify(builder.active.draft),
      ),
    [builder.active, builder.draft],
  );
  const canPublish = Boolean(
    builder.active &&
    builder.draft &&
    !dirty &&
    builder.draft.revision > builder.active.last_published_revision,
  );

  const selectCategory = (category: Parameters<typeof builder.select>[0]) => {
    builder.select(category);
    setMobilePanel("editor");
  };

  const homeCategory = builder.categories.find((category) => category.is_home) ?? null;
  const listCategories = builder.categories.filter((category) => !category.is_home);

  return (
    <ContentEditorResourcesProvider>
    <div className="page content-builder-page">
      <div className="page-head content-builder-head">
        <div>
          <h1 className="page-title">Контент мини-приложения</h1>
          <p className="page-sub">
            Категории, визуальные блоки, предпросмотр и публикация без правок
            кода.
          </p>
        </div>
        <div className="content-head-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setSharedDraftsOpen(true)}
          >
            Общие черновики
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setCreatingShortcutParentId(null)}
          >
            Ссылка на возможность
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setCreatingParentId(null)}
          >
            Новая категория
          </button>
        </div>
      </div>

      {sharedDraftsOpen ? (
        <SharedContentDraftPicker
          existingSlugs={builder.categories.map((category) => category.slug)}
          onImport={async (sourceCategoryId, slug, resolutions) => {
            await builder.importSharedDraft(sourceCategoryId, slug, resolutions);
            setMobilePanel("editor");
          }}
          onClose={() => setSharedDraftsOpen(false)}
        />
      ) : null}

      {creatingParentId !== undefined ? (
        <CreateCategoryForm
          order={listCategories.filter((category) => category.parent_id === creatingParentId).length}
          categories={listCategories}
          initialParentId={creatingParentId}
          onCreate={builder.create}
          onCancel={() => setCreatingParentId(undefined)}
        />
      ) : null}

      {creatingShortcutParentId !== undefined ? (
        <CapabilityShortcutForm
          mode="create"
          order={listCategories.filter((category) => category.parent_id === creatingShortcutParentId).length}
          categories={listCategories}
          initialParentId={creatingShortcutParentId}
          onCreate={builder.create}
          onCancel={() => setCreatingShortcutParentId(undefined)}
        />
      ) : null}

      <div
        className="content-mobile-tabs"
        role="tablist"
        aria-label="Раздел конструктора"
      >
        {(["categories", "editor", "preview"] as MobilePanel[]).map((panel) => (
          <button
            type="button"
            role="tab"
            aria-selected={mobilePanel === panel}
            className={mobilePanel === panel ? "active" : ""}
            key={panel}
            onClick={() => setMobilePanel(panel)}
          >
            {panel === "categories"
              ? "Категории"
              : panel === "editor"
                ? "Редактор"
                : "Preview"}
          </button>
        ))}
      </div>

      {builder.error ? (
        <div className="content-status content-status--error">
          <span>{builder.error}</span>
          <button
            type="button"
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

      <div className="content-builder-layout">
        <aside
          className={`card content-builder-categories content-mobile-panel ${mobilePanel === "categories" ? "active" : ""}`}
        >
          <div className="card-head">
            <div>
              <h2 className="card-title">Категории</h2>
              <p className="card-sub">Порядок карточек на главной</p>
            </div>
            <span className="tag neutral">{builder.categories.length}</span>
          </div>
          <div className="card-body">
            {builder.loading ? (
              <p className="muted">Загрузка…</p>
            ) : (
              <>
                {homeCategory ? (
                  <article
                    className={`content-category-row content-category-row--home ${builder.active?.id === homeCategory.id ? "active" : ""}`}
                  >
                    <button
                      type="button"
                      className="content-category-row__select"
                      onClick={() => selectCategory(homeCategory)}
                    >
                      <span className="content-category-icon" aria-hidden="true">
                        <ContentIcon name={homeCategory.icon} />
                      </span>
                      <span>
                        <strong>Главный экран</strong>
                        <small>приветствие и блоки</small>
                      </span>
                    </button>
                  </article>
                ) : null}
                <CategoryList
                  categories={listCategories}
                  activeId={builder.active?.id ?? null}
                  reordering={builder.busy === "reorder"}
                  onSelect={selectCategory}
                  onMove={(id, direction) => void builder.move(id, direction)}
                  onAddChild={(id) => setCreatingParentId(id)}
                  onAddShortcut={(id) => setCreatingShortcutParentId(id)}
                />
              </>
            )}
          </div>
        </aside>

        <section
          className={`card content-builder-editor content-mobile-panel ${mobilePanel === "editor" ? "active" : ""}`}
        >
          {!builder.active ? (
            <div className="content-empty-state content-empty-state--large">
              <strong>Выберите категорию</strong>
              <span>Здесь появятся настройки страницы и визуальные блоки.</span>
            </div>
          ) : isShortcutCategory(builder.active) ? (
            <div className="card-body">
              <CapabilityShortcutForm
                key={builder.active.id}
                mode="edit"
                category={builder.active}
                onSave={builder.patchShortcutCard}
                onCancel={() => {}}
              />
            </div>
          ) : !builder.draft ? (
            <div className="content-empty-state content-empty-state--large">
              <strong>Выберите категорию</strong>
              <span>Здесь появятся настройки страницы и визуальные блоки.</span>
            </div>
          ) : (
            <>
              <div className="card-head content-builder-toolbar">
                <div>
                  <h2 className="card-title">
                    {builder.draft.title || "Без названия"}
                  </h2>
                  <p className="card-sub">
                    Черновик · ревизия {builder.draft.revision}
                  </p>
                </div>
                <div className="content-toolbar-actions">
                  {!builder.active.is_home ? (
                    <label className="content-checkbox">
                      <input
                        type="checkbox"
                        checked={builder.active.is_active}
                        onChange={(event) =>
                          void builder.patchVisibility(
                            builder.active!,
                            event.target.checked,
                          )
                        }
                      />
                      Показывать
                    </label>
                  ) : null}
                  {!builder.active.is_home ? (
                    <label
                      className="content-checkbox"
                      title="Другие администраторы смогут скопировать этот черновик в свой бот"
                    >
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
                  ) : null}
                  <button
                    type="button"
                    className="btn btn-secondary"
                    disabled={!dirty || builder.busy !== null}
                    onClick={() => void builder.save()}
                  >
                    {builder.busy === "save" ? "Сохранение…" : "Сохранить"}
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary"
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
                </div>
              </div>
              {dirty ? (
                <div className="content-unsaved">
                  Есть несохранённые изменения. Сначала сохраните черновик.
                </div>
              ) : null}
              {!builder.active.published_version_id ? (
                <div className="content-unpublished">
                  Категория ещё не публиковалась и не видна пользователям.
                </div>
              ) : null}
              <div className="card-body">
                <ContentDraftEditor
                  category={builder.active}
                  draft={builder.draft}
                  categories={listCategories}
                  onChange={builder.setDraft}
                  onIconChange={(icon) =>
                    void builder.patchIcon(builder.active!, icon)
                  }
                  onParentChange={(parentId) =>
                    void builder.patchParent(builder.active!, parentId)
                  }
                />
              </div>
            </>
          )}
        </section>

        <aside
          className={`card content-builder-preview content-mobile-panel ${mobilePanel === "preview" ? "active" : ""}`}
        >
          <div className="card-head">
            <div>
              <h2 className="card-title">Предпросмотр</h2>
              <p className="card-sub">Как выглядит сохранённая версия в мини-приложении</p>
            </div>
          </div>
          <div className="card-body">
            {builder.active && builder.draft ? (
              <ContentPreviewFrame categoryId={builder.active.id} revision={builder.draft.revision} />
            ) : (
              <div className="content-empty-state">
                <span>Выберите категорию</span>
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
    </ContentEditorResourcesProvider>
  );
}
