import { useState } from "react";

import type {
  StaffAccess,
  StaffPermissions,
} from "@/features/staff-access/model/types";
import { PermissionFields } from "@/features/staff-access/ui/PermissionFields";

export function StaffAccessCard({
  access,
  isSelf,
  onUpdate,
  onRevoke,
}: {
  access: StaffAccess;
  isSelf: boolean;
  onUpdate: (permissions: StaffPermissions) => Promise<unknown>;
  onRevoke: () => Promise<unknown>;
}) {
  const [draft, setDraft] = useState(access.permissions);
  const [saving, setSaving] = useState(false);

  const changed = JSON.stringify(draft) !== JSON.stringify(access.permissions);

  return (
    <article className="card staff-access-card">
      <div className="staff-access-card__identity">
        <div>
          <h2>{access.full_name}</h2>
          <div className="mono">MAX ID: {access.max_user_id}</div>
        </div>
        <span className="badge">
          {access.role === "platform_admin"
            ? "Админ платформы"
            : access.role === "admin"
              ? "Администратор"
              : "Сотрудник"}
        </span>
      </div>
      <PermissionFields
        value={draft}
        onChange={(next) => {
          if (isSelf && !next.can_manage_staff) return;
          setDraft(next);
        }}
      />
      <div className="staff-access-card__actions">
        <button
          className="btn btn-primary btn-sm"
          disabled={!changed || saving}
          onClick={() => {
            setSaving(true);
            void onUpdate(draft)
              .catch((reason) => {
                setDraft(access.permissions);
                window.alert((reason as Error).message);
              })
              .finally(() => setSaving(false));
          }}
        >
          {saving ? "Сохранение…" : "Сохранить права"}
        </button>
        {!isSelf ? (
          <button
            className="btn btn-danger btn-sm"
            onClick={() => {
              if (window.confirm(`Отозвать доступ у ${access.full_name}?`)) {
                void onRevoke().catch((reason) =>
                  window.alert((reason as Error).message),
                );
              }
            }}
          >
            Отозвать доступ
          </button>
        ) : (
          <span className="muted">Ваш текущий доступ</span>
        )}
      </div>
    </article>
  );
}
