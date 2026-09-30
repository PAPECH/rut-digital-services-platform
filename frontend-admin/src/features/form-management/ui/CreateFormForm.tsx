import { useState } from "react";
import type { FormCreate } from "@/entities/form/model/types";
import { slugify } from "@/shared/lib/slugify";
export function CreateFormForm({
  order,
  onCreate,
  onCancel,
}: {
  order: number;
  onCreate: (payload: FormCreate) => Promise<unknown>;
  onCancel: () => void;
}) {
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <form
      className="card content-create-form"
      onSubmit={(e) => {
        e.preventDefault();
        setBusy(true);
        void onCreate({
          slug,
          name,
          description: null,
          reply_on_accept: null,
          order,
        })
          .then(onCancel)
          .finally(() => setBusy(false));
      }}
    >
      <div className="card-body content-editor-grid">
        <label className="content-editor-field">
          <span>Название</span>
          <input
            className="input"
            required
            value={name}
            onChange={(e) => {
              const value = e.target.value;
              setName(value);
              if (!slugTouched) setSlug(slugify(value));
            }}
          />
        </label>
        <label className="content-editor-field">
          <span>Системный slug</span>
          <input
            className="input"
            required
            minLength={2}
            maxLength={80}
            pattern="[a-z0-9](?:[a-z0-9_]|-){1,79}"
            value={slug}
            onChange={(e) => {
              setSlugTouched(true);
              setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""));
            }}
          />
        </label>
        <div className="content-toolbar-actions">
          <button
            className="btn btn-secondary"
            type="button"
            onClick={onCancel}
          >
            Отмена
          </button>
          <button className="btn btn-primary" disabled={busy} type="submit">
            {busy ? "Создание…" : "Создать"}
          </button>
        </div>
      </div>
    </form>
  );
}
