import { useEffect, useState } from "react";

import {
  DEFAULT_STAFF_PERMISSIONS,
  type GrantStaffAccessDraft,
} from "@/features/staff-access/model/types";
import { PermissionFields } from "@/features/staff-access/ui/PermissionFields";

const emptyDraft = (): GrantStaffAccessDraft => ({
  max_user_id: "",
  full_name: "",
  role: "employee",
  permissions: { ...DEFAULT_STAFF_PERMISSIONS },
});

export function GrantStaffAccessForm({
  saving,
  onGrant,
}: {
  saving: boolean;
  onGrant: (draft: GrantStaffAccessDraft) => Promise<unknown>;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(emptyDraft);
  const [error, setError] = useState<string | null>(null);

  const close = () => {
    if (saving) return;
    setOpen(false);
    setError(null);
  };

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, saving]);

  return (
    <>
      <button type="button" className="btn btn-primary" onClick={() => setOpen(true)}>
        Добавить сотрудника
      </button>
      {open ? (
        <div className="staff-grant-backdrop" role="presentation" onMouseDown={close}>
          <section
            className="staff-grant-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="staff-grant-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="staff-grant-dialog__head">
              <div>
                <h2 id="staff-grant-title">Добавить сотрудника</h2>
                <p>Доступ будет выдан только к выбранному боту.</p>
              </div>
              <button type="button" className="btn btn-ghost btn-sm" disabled={saving} onClick={close}>
                Закрыть
              </button>
            </div>
            <form
              className="staff-grant-form"
              onSubmit={(event) => {
                event.preventDefault();
                setError(null);
                void onGrant(draft)
                  .then(() => {
                    setDraft(emptyDraft());
                    setOpen(false);
                  })
                  .catch((reason) => setError((reason as Error).message));
              }}
            >
              <div className="staff-grant-form__identity">
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
                  <span className="field-label">Тип доступа</span>
                  <select
                    className="select"
                    value={draft.role}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        role: event.target.value as "employee" | "admin",
                      }))
                    }
                  >
                    <option value="employee">Сотрудник</option>
                    <option value="admin">Администратор бота</option>
                  </select>
                </label>
                <label className="staff-grant-form__wide">
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
              </div>
              <div className="staff-grant-form__permissions">
                <div className="staff-grant-form__permissions-head">
                  <div>
                    <strong>Разрешения в боте</strong>
                    <span>Можно изменить позднее в карточке сотрудника.</span>
                  </div>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => {
                      const allSelected = Object.values(draft.permissions).every(Boolean);
                      setDraft((current) => {
                        const permissions = { ...current.permissions };
                        for (const key of Object.keys(permissions) as Array<
                          keyof typeof permissions
                        >) {
                          permissions[key] = !allSelected;
                        }
                        return { ...current, permissions };
                      });
                    }}
                  >
                    {Object.values(draft.permissions).every(Boolean) ? "Снять все" : "Выбрать все"}
                  </button>
                </div>
                <PermissionFields
                  value={draft.permissions}
                  onChange={(permissions) =>
                    setDraft((current) => ({ ...current, permissions }))
                  }
                />
              </div>
              {error ? <p className="form-error staff-grant-form__error">{error}</p> : null}
              <div className="staff-grant-form__actions">
                <button type="button" className="btn btn-ghost" disabled={saving} onClick={close}>
                  Отмена
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={saving || !draft.max_user_id.trim() || !draft.full_name.trim()}
                >
                  {saving ? "Добавление…" : "Выдать доступ"}
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </>
  );
}
