import { useState } from "react";

import type { TestCreate } from "@/entities/form-test/model/types";
import { slugify } from "@/shared/lib/slugify";

export function CreateTestForm({
  order,
  onCreate,
  onCancel,
}: {
  order: number;
  onCreate: (payload: TestCreate) => Promise<unknown>;
  onCancel: () => void;
}) {
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <form
      className="card"
      onSubmit={(event) => {
        event.preventDefault();
        setBusy(true);
        setError(null);
        void onCreate({ slug, name, order })
          .then(onCancel)
          .catch((err: unknown) => {
            setError(err instanceof Error ? err.message : "Не удалось создать тест");
          })
          .finally(() => setBusy(false));
      }}
    >
      <div className="card-body">
        <label>
          <span>Название теста</span>
          <input
            className="input"
            required
            value={name}
            onChange={(event) => {
              const value = event.target.value;
              setName(value);
              if (!slugTouched) setSlug(slugify(value));
            }}
          />
        </label>
        <label>
          <span>Системный slug</span>
          <input
            className="input"
            required
            minLength={2}
            maxLength={80}
            pattern="[a-z0-9](?:[a-z0-9_]|-){1,79}"
            value={slug}
            onChange={(event) => {
              setSlugTouched(true);
              setSlug(event.target.value.toLowerCase().replace(/[^a-z0-9_-]/g, ""));
            }}
          />
        </label>
        {error && <div>{error}</div>}
        <div>
          <button className="btn btn-secondary" type="button" onClick={onCancel}>
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
