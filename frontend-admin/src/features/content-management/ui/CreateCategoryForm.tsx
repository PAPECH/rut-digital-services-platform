import { useState } from "react";

import type { ContentIconName } from "@/entities/content/model/contentIcons";
import type {
  AdminContentCategory,
  ContentCategoryCreate,
} from "@/entities/content/model/types";
import { ContentIconPicker } from "@/entities/content/ui/ContentIconPicker";
import { availableNewCategoryParents } from "@/features/content-management/model/categoryTree";
import { slugify } from "@/shared/lib/slugify";

export function CreateCategoryForm({
  order,
  categories,
  initialParentId,
  onCreate,
  onCancel,
}: {
  order: number;
  categories: AdminContentCategory[];
  initialParentId: number | null;
  onCreate: (payload: ContentCategoryCreate) => Promise<unknown>;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [icon, setIcon] = useState<ContentIconName>("folder");
  const [language, setLanguage] = useState("ru");
  const [parentId, setParentId] = useState<number | null>(initialParentId);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onCreate({
        title,
        slug,
        parent_id: parentId,
        icon,
        subtitle: null,
        language,
        order,
      });
      onCancel();
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Не удалось создать категорию",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form
      className="card content-create-card"
      onSubmit={(event) => void submit(event)}
    >
      <div className="card-head">
        <div>
          <h2 className="card-title">Новая категория</h2>
          <p className="card-sub">Адрес нельзя изменить после создания.</p>
        </div>
      </div>
      <div className="card-body content-create-form">
        <label>
          <span className="field-label">Название</span>
          <input
            autoFocus
            required
            maxLength={300}
            className="input"
            value={title}
            onChange={(event) => {
              const value = event.target.value;
              setTitle(value);
              if (!slugTouched) setSlug(slugify(value));
            }}
          />
        </label>
        <label>
          <span className="field-label">Адрес (slug)</span>
          <input
            required
            minLength={2}
            maxLength={80}
            pattern="[a-z0-9](?:[a-z0-9_]|-){1,79}"
            className="input"
            value={slug}
            onChange={(event) => {
              setSlugTouched(true);
              setSlug(event.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""));
            }}
            placeholder="business-trips"
          />
        </label>
        <label>
          <span className="field-label">Иконка</span>
          <ContentIconPicker value={icon} onChange={setIcon} />
        </label>
        <label>
          <span className="field-label">Язык</span>
          <select className="select" value={language} onChange={(event) => setLanguage(event.target.value)}>
            <option value="ru">Русский</option>
            <option value="en">English</option>
          </select>
        </label>
        <label className="content-editor-wide">
          <span className="field-label">Родительская категория</span>
          <select
            className="select"
            value={parentId ?? ""}
            onChange={(event) => setParentId(event.target.value ? Number(event.target.value) : null)}
          >
            <option value="">Корневая категория</option>
            {availableNewCategoryParents(categories).map((category) => (
              <option value={category.id} key={category.id}>{category.draft?.title ?? category.slug}</option>
            ))}
          </select>
        </label>
        {error ? (
          <p className="form-error content-editor-wide">{error}</p>
        ) : null}
        <div className="content-form-actions content-editor-wide">
          <button type="button" className="btn btn-ghost" onClick={onCancel}>
            Отмена
          </button>
          <button
            disabled={submitting}
            className="btn btn-primary"
            type="submit"
          >
            {submitting ? "Создание…" : "Создать"}
          </button>
        </div>
      </div>
    </form>
  );
}
