import { useEffect, useMemo, useState } from "react";

import { copyDraftSlug } from "../model/copyDraftSlug";

export interface SharedDraftListItem {
  id: number;
  slug: string;
  title: string;
  description: string | null;
  sourceBotName: string;
  meta?: string;
}

export function SharedDraftPicker({
  title,
  itemLabel,
  existingSlugs,
  loadItems,
  onImport,
  onClose,
}: {
  title: string;
  itemLabel: string;
  existingSlugs: string[];
  loadItems: () => Promise<SharedDraftListItem[]>;
  onImport: (item: SharedDraftListItem, slug: string) => Promise<unknown>;
  onClose: () => void;
}) {
  const [items, setItems] = useState<SharedDraftListItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [slug, setSlug] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const occupied = useMemo(() => new Set(existingSlugs), [existingSlugs]);
  const selected = items.find((item) => item.id === selectedId) ?? null;

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    void loadItems()
      .then((loaded) => {
        if (!mounted) return;
        setItems(loaded);
        const first = loaded[0] ?? null;
        setSelectedId(first?.id ?? null);
        setSlug(first ? copyDraftSlug(first.slug, occupied) : "");
      })
      .catch((loadError: unknown) => {
        if (mounted)
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Не удалось загрузить общие черновики",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [loadItems, occupied]);

  const selectItem = (item: SharedDraftListItem) => {
    setSelectedId(item.id);
    setSlug(copyDraftSlug(item.slug, occupied));
    setError(null);
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selected) return;
    setSubmitting(true);
    setError(null);
    try {
      await onImport(selected, slug);
      onClose();
    } catch (importError) {
      setError(
        importError instanceof Error
          ? importError.message
          : "Не удалось скопировать черновик",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="shared-draft-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="shared-draft-dialog"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="card-head">
          <div>
            <h2 className="card-title">{title}</h2>
            <p className="card-sub">Будет создана независимая копия в текущем боте.</p>
          </div>
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Закрыть
          </button>
        </div>
        <form className="shared-draft-body" onSubmit={(event) => void submit(event)}>
          {loading ? <p className="muted">Загрузка…</p> : null}
          {!loading && !items.length ? (
            <div className="content-empty-state">
              <strong>Общих черновиков пока нет</strong>
              <span>Сотрудник должен сохранить черновик с отметкой «Общий».</span>
            </div>
          ) : null}
          <div className="shared-draft-list">
            {items.map((item) => (
              <button
                type="button"
                className={`shared-draft-item ${selectedId === item.id ? "active" : ""}`}
                key={item.id}
                onClick={() => selectItem(item)}
              >
                <strong>{item.title}</strong>
                <span>{item.description || `Без описания ${itemLabel}`}</span>
                <small>{item.sourceBotName} · /{item.slug}{item.meta ? ` · ${item.meta}` : ""}</small>
              </button>
            ))}
          </div>
          {selected ? (
            <label>
              <span className="field-label">Адрес новой копии (slug)</span>
              <input
                required
                minLength={2}
                maxLength={80}
                pattern="[a-z0-9](?:[a-z0-9_]|-){1,79}"
                className="input"
                value={slug}
                onChange={(event) =>
                  setSlug(
                    event.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""),
                  )
                }
              />
            </label>
          ) : null}
          {error ? <p className="form-error">{error}</p> : null}
          <div className="content-form-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              Отмена
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={!selected || submitting}
            >
              {submitting ? "Копирование…" : "Создать копию"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
