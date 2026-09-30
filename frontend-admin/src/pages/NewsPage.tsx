import { useCallback, useEffect, useRef, useState } from "react";
import { Icon } from "@/components/Icon";
import { isImageMime, uploadFile } from "@/api/files";
import type { NewsBodyBlock } from "@/entities/content/model/types";
import { ContentEditorResourcesProvider } from "@/features/content-management/model/ContentEditorResourcesContext";
import { NewsBodyEditor } from "@/features/news-management/ui/NewsBodyEditor";
import { newsApi, type NewsItem, type NewsItemInput } from "@/features/news-management/api/newsApi";

interface Draft {
  id: number | null;
  title: string;
  title_en: string;
  category: string;
  body_blocks: NewsBodyBlock[];
  cover_attachment_id: number | null;
  cover_url: string | null;
  is_active: boolean;
  published_at: string;
}

function toLocalDateTimeInput(iso: string): string {
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function emptyDraft(): Draft {
  return {
    id: null,
    title: "",
    title_en: "",
    category: "",
    body_blocks: [{ id: `p_${crypto.randomUUID().slice(0, 12)}`, type: "paragraph", text: "" }],
    cover_attachment_id: null,
    cover_url: null,
    is_active: true,
    published_at: toLocalDateTimeInput(new Date().toISOString()),
  };
}

export function NewsPage() {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    void newsApi.list().then(setItems).catch(() => setItems([]));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const openCreate = () => setDraft(emptyDraft());
  const openEdit = (item: NewsItem) =>
    setDraft({
      id: item.id,
      title: item.title,
      title_en: item.title_en ?? "",
      category: item.category ?? "",
      body_blocks: item.body_blocks,
      cover_attachment_id: item.cover_attachment_id,
      cover_url: item.cover_url,
      is_active: item.is_active,
      published_at: toLocalDateTimeInput(item.published_at),
    });

  const save = async () => {
    if (!draft) return;
    if (!draft.title.trim()) {
      setError("Заполните заголовок");
      return;
    }
    if (draft.body_blocks.length === 0) {
      setError("Добавьте хотя бы один блок текста");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const body: NewsItemInput = {
        title: draft.title.trim(),
        title_en: draft.title_en.trim() || null,
        body_blocks: draft.body_blocks,
        category: draft.category.trim() || null,
        cover_attachment_id: draft.cover_attachment_id,
        is_active: draft.is_active,
        published_at: new Date(draft.published_at).toISOString(),
      };
      if (draft.id == null) {
        await newsApi.create(body);
      } else {
        await newsApi.update(draft.id, body);
      }
      setDraft(null);
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (item: NewsItem) => {
    if (!confirm(`Удалить новость «${item.title.slice(0, 50)}»?`)) return;
    await newsApi.remove(item.id);
    reload();
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Новости</h1>
          <p className="page-sub">Лента новостей, которую видит студент в mini-app</p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>
          <span className="ico" style={{ width: 14, height: 14 }}>
            <Icon.Plus />
          </span>
          Добавить
        </button>
      </div>

      <div className="card">
        {items.length === 0 ? (
          <div style={{ padding: 32, textAlign: "center", color: "var(--ink-400)" }}>
            Новостей пока нет
          </div>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              style={{
                display: "flex",
                gap: 12,
                alignItems: "flex-start",
                padding: "14px 18px",
                borderBottom: "1px solid var(--line)",
              }}
            >
              {item.cover_url ? (
                <img
                  src={item.cover_url}
                  alt=""
                  style={{ width: 64, height: 64, objectFit: "cover", borderRadius: 8, flexShrink: 0 }}
                />
              ) : null}
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{item.title}</span>
                  {!item.is_active && <span className="tag neutral">скрыта</span>}
                  {item.category ? (
                    <span className="tag outline" style={{ fontSize: 11 }}>
                      {item.category}
                    </span>
                  ) : null}
                </div>
                <div style={{ fontSize: 12, color: "var(--ink-400)" }}>
                  {new Date(item.published_at).toLocaleString("ru-RU")}
                </div>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <button className="btn btn-secondary btn-sm" onClick={() => openEdit(item)}>
                  Изменить
                </button>
                <button className="btn btn-danger btn-sm" onClick={() => void remove(item)}>
                  Удалить
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {draft && (
        <ContentEditorResourcesProvider>
          <NewsDrawer draft={draft} setDraft={setDraft} onClose={() => setDraft(null)} onSave={save} busy={busy} error={error} />
        </ContentEditorResourcesProvider>
      )}
    </div>
  );
}

function NewsDrawer({
  draft,
  setDraft,
  onClose,
  onSave,
  busy,
  error,
}: {
  draft: Draft;
  setDraft: (d: Draft) => void;
  onClose: () => void;
  onSave: () => void | Promise<void>;
  busy: boolean;
  error: string | null;
}) {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const pickCover = async (file: File) => {
    setUploading(true);
    try {
      const uploaded = await uploadFile(file);
      setDraft({ ...draft, cover_attachment_id: uploaded.id, cover_url: uploaded.url });
    } catch (e) {
      alert((e as Error).message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex", justifyContent: "flex-end" }}>
      <div onClick={onClose} style={{ position: "absolute", inset: 0, background: "rgba(11,23,41,.32)" }} />
      <div
        style={{
          position: "relative",
          width: 680,
          maxWidth: "100vw",
          height: "100%",
          background: "#fff",
          borderLeft: "1px solid var(--line)",
          boxShadow: "var(--shadow-lg)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            padding: "18px 22px",
            borderBottom: "1px solid var(--line)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h3 style={{ margin: 0, fontSize: 16 }}>{draft.id == null ? "Новая новость" : `Новость #${draft.id}`}</h3>
          <button className="btn btn-ghost btn-icon" onClick={onClose}>
            ×
          </button>
        </div>
        <div style={{ padding: 22, overflow: "auto", flex: 1 }}>
          <label className="field-label">Заголовок *</label>
          <input className="input" value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} />

          <label className="field-label" style={{ marginTop: 12 }}>
            Title (EN)
          </label>
          <input className="input" value={draft.title_en} onChange={(e) => setDraft({ ...draft, title_en: e.target.value })} />

          <div style={{ display: "flex", gap: 16, marginTop: 12 }}>
            <div style={{ flex: 1 }}>
              <label className="field-label">Категория</label>
              <input
                className="input"
                placeholder="например, Спорт"
                value={draft.category}
                onChange={(e) => setDraft({ ...draft, category: e.target.value })}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label className="field-label">Дата публикации</label>
              <input
                className="input"
                type="datetime-local"
                value={draft.published_at}
                onChange={(e) => setDraft({ ...draft, published_at: e.target.value })}
              />
            </div>
          </div>

          <label className="field-label" style={{ marginTop: 12 }}>
            Обложка
          </label>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            {draft.cover_url ? (
              <img src={draft.cover_url} alt="" style={{ width: 72, height: 72, objectFit: "cover", borderRadius: 8 }} />
            ) : null}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file && isImageMime(file.type)) void pickCover(file);
                e.target.value = "";
              }}
            />
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
            >
              {uploading ? "Загрузка…" : draft.cover_url ? "Заменить" : "Загрузить изображение"}
            </button>
            {draft.cover_url ? (
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setDraft({ ...draft, cover_attachment_id: null, cover_url: null })}
              >
                Убрать
              </button>
            ) : null}
          </div>

          <label className="field-label" style={{ marginTop: 16 }}>
            Текст новости *
          </label>
          <NewsBodyEditor blocks={draft.body_blocks} onChange={(body_blocks) => setDraft({ ...draft, body_blocks })} />

          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, marginTop: 16 }}>
            <input type="checkbox" checked={draft.is_active} onChange={(e) => setDraft({ ...draft, is_active: e.target.checked })} />
            Активна
          </label>

          {error && <div style={{ marginTop: 12, color: "var(--st-rej-fg)", fontSize: 13 }}>{error}</div>}
        </div>
        <div style={{ padding: 16, borderTop: "1px solid var(--line)", display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={busy}>
            Отмена
          </button>
          <button className="btn btn-primary" onClick={() => void onSave()} disabled={busy}>
            {busy ? "Сохраняем…" : "Сохранить"}
          </button>
        </div>
      </div>
    </div>
  );
}
