import { useState } from "react";

import type {
  EnsurePlatformAdminDraft,
  EnsurePlatformAdminResult,
} from "@/features/platform-admin-management/model/types";

const EMPTY_DRAFT: EnsurePlatformAdminDraft = { max_user_id: "", full_name: "" };

export function CreatePlatformAdminForm({
  saving,
  externalError,
  onEnsure,
}: {
  saving: boolean;
  externalError: string | null;
  onEnsure: (draft: EnsurePlatformAdminDraft) => Promise<EnsurePlatformAdminResult>;
}) {
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [notice, setNotice] = useState<string | null>(null);

  return (
    <form
      className="platform-admin-create"
      onSubmit={(event) => {
        event.preventDefault();
        setNotice(null);
        void onEnsure(draft)
          .then((result) => {
            setDraft(EMPTY_DRAFT);
            setNotice(
              result.created
                ? "Администратор платформы создан."
                : result.promoted
                  ? "Существующий сотрудник повышен до администратора платформы."
                  : result.reactivated
                    ? "Администратор платформы снова активен."
                    : "Данные администратора платформы обновлены.",
            );
          })
          .catch(() => undefined);
      }}
    >
      <div className="platform-admin-create__intro">
        <strong>Добавить администратора платформы</strong>
        <span>
          После добавления человек сможет войти через свой MAX и управлять всеми ботами.
        </span>
      </div>
      <label>
        <span className="field-label">MAX ID</span>
        <input
          className="input"
          inputMode="numeric"
          autoComplete="off"
          placeholder="Например, 123456789"
          value={draft.max_user_id}
          onChange={(event) =>
            setDraft((current) => ({ ...current, max_user_id: event.target.value.trim() }))
          }
        />
      </label>
      <label>
        <span className="field-label">ФИО</span>
        <input
          className="input"
          autoComplete="name"
          placeholder="Иванов Иван Иванович"
          value={draft.full_name}
          onChange={(event) =>
            setDraft((current) => ({ ...current, full_name: event.target.value }))
          }
        />
      </label>
      <button
        type="submit"
        className="btn btn-primary"
        disabled={saving || !draft.max_user_id.trim() || !draft.full_name.trim()}
      >
        {saving ? "Сохранение…" : "Добавить"}
      </button>
      {externalError ? <p className="form-error platform-admin-create__message">{externalError}</p> : null}
      {notice ? <p className="form-success platform-admin-create__message">{notice}</p> : null}
    </form>
  );
}
