import type { SharedContentDraft } from "@/entities/content/model/types";

export function SharedContentDraftSelection({
  items,
  selectedId,
  slug,
  onSelect,
  onSlugChange,
}: {
  items: SharedContentDraft[];
  selectedId: number | null;
  slug: string;
  onSelect: (item: SharedContentDraft) => void;
  onSlugChange: (slug: string) => void;
}) {
  const selected = items.find((item) => item.source_category_id === selectedId) ?? null;
  return (
    <>
      <div className="shared-draft-list">
        {items.map((item) => (
          <button
            type="button"
            className={`shared-draft-item ${selectedId === item.source_category_id ? "active" : ""}`}
            key={item.source_category_id}
            onClick={() => onSelect(item)}
          >
            <strong>{item.title}</strong>
            <span>{item.subtitle || "Без описания категории"}</span>
            <small>
              {item.source_bot_name} · /{item.slug} · {item.language.toUpperCase()}
            </small>
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
              onSlugChange(
                event.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""),
              )
            }
          />
        </label>
      ) : null}
    </>
  );
}
