import { useEffect, useState } from "react";

import {
  INVITE_TTL_OPTIONS,
  type AdminInviteDraft,
  type CreatedAdminInvite,
  type InviteScope,
} from "@/features/admin-invites/model/types";
import * as css from "@/features/admin-invites/ui/adminInvites.css";
import { InviteLinkResult } from "@/features/admin-invites/ui/InviteLinkResult";
import { DEFAULT_STAFF_PERMISSIONS } from "@/features/staff-access/model/types";
import { PermissionFields } from "@/features/staff-access/ui/PermissionFields";

const emptyDraft = (): AdminInviteDraft => ({
  full_name: "",
  ttl_hours: 168,
  max_uses: 1,
  role: "employee",
  permissions: { ...DEFAULT_STAFF_PERMISSIONS },
});

export function CreateInviteDialog({
  scope,
  saving,
  onCreate,
}: {
  scope: InviteScope;
  saving: boolean;
  onCreate: (draft: AdminInviteDraft) => Promise<CreatedAdminInvite>;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(emptyDraft);
  const [created, setCreated] = useState<CreatedAdminInvite | null>(null);
  const [error, setError] = useState<string | null>(null);

  const close = () => {
    if (saving) return;
    setOpen(false);
    setCreated(null);
    setError(null);
    setDraft(emptyDraft());
  };

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, saving]);

  const submit = () => {
    setError(null);
    void onCreate(draft)
      .then(setCreated)
      .catch((reason) => setError((reason as Error).message));
  };

  const title = scope === "platform" ? "Пригласить администратора платформы" : "Пригласить сотрудника";

  return (
    <>
      <button type="button" className="btn btn-ghost" onClick={() => setOpen(true)}>
        Пригласить по ссылке
      </button>
      {open ? (
        <div className="staff-grant-backdrop" role="presentation" onMouseDown={close}>
          <section
            className="staff-grant-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby={`invite-title-${scope}`}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="staff-grant-dialog__head">
              <div>
                <h2 id={`invite-title-${scope}`}>{title}</h2>
                <p>
                  {scope === "platform"
                    ? "Получит глобальный доступ ко всем ботам."
                    : "Доступ будет выдан только к выбранному боту."}
                </p>
              </div>
              <button type="button" className="btn btn-ghost btn-sm" disabled={saving} onClick={close}>
                Закрыть
              </button>
            </div>
            {created ? (
              <InviteLinkResult created={created} />
            ) : (
              <form
                className="staff-grant-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  submit();
                }}
              >
                <label>
                  <span className="field-label">ФИО</span>
                  <input
                    className="input"
                    autoComplete="off"
                    placeholder="Иванов Иван Иванович"
                    value={draft.full_name}
                    onChange={(event) =>
                      setDraft((current) => ({ ...current, full_name: event.target.value }))
                    }
                  />
                </label>
                <div className={css.fieldRow}>
                  <label>
                    <span className="field-label">Срок действия</span>
                    <select
                      className="select"
                      value={draft.ttl_hours}
                      onChange={(event) =>
                        setDraft((current) => ({ ...current, ttl_hours: Number(event.target.value) }))
                      }
                    >
                      {INVITE_TTL_OPTIONS.map((option) => (
                        <option key={option.hours} value={option.hours}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span className="field-label">Сколько раз можно использовать</span>
                    <input
                      className="input"
                      type="number"
                      min={1}
                      max={100}
                      value={draft.max_uses}
                      onChange={(event) =>
                        setDraft((current) => ({
                          ...current,
                          max_uses: Math.min(100, Math.max(1, Number(event.target.value) || 1)),
                        }))
                      }
                    />
                  </label>
                </div>
                {scope === "bot" ? (
                  <>
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
                    <div className="staff-grant-form__permissions">
                      <div className="staff-grant-form__permissions-head">
                        <div>
                          <strong>Разрешения в боте</strong>
                        </div>
                      </div>
                      <PermissionFields
                        value={draft.permissions}
                        onChange={(permissions) =>
                          setDraft((current) => ({ ...current, permissions }))
                        }
                      />
                    </div>
                  </>
                ) : null}
                {error ? <p className="form-error staff-grant-form__error">{error}</p> : null}
                <div className="staff-grant-form__actions">
                  <button type="button" className="btn btn-ghost" disabled={saving} onClick={close}>
                    Отмена
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={saving || !draft.full_name.trim()}
                  >
                    {saving ? "Создание…" : "Создать ссылку"}
                  </button>
                </div>
              </form>
            )}
          </section>
        </div>
      ) : null}
    </>
  );
}
