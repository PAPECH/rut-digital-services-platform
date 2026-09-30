import { useState } from "react";

import type { CreatedAdminInvite } from "@/features/admin-invites/model/types";
import * as css from "@/features/admin-invites/ui/adminInvites.css";

export function InviteLinkResult({ created }: { created: CreatedAdminInvite }) {
  const [copied, setCopied] = useState(false);
  const value = created.link ?? created.start_param;

  const copy = () => {
    void navigator.clipboard
      .writeText(value)
      .then(() => setCopied(true))
      .catch(() => setCopied(false));
  };

  return (
    <div className={css.linkBox}>
      <span className="field-label">
        {created.link ? "Ссылка-приглашение" : "Параметр startapp для бота админки"}
      </span>
      <div className={css.linkValue}>{value}</div>
      <button type="button" className="btn btn-primary" onClick={copy}>
        {copied ? "Скопировано" : "Скопировать"}
      </button>
      <p className={css.warning}>
        Ссылка показывается один раз. Человек открывает её в MAX и сразу попадает в
        админ-панель. Действует до {new Date(created.invite.expires_at).toLocaleString("ru-RU")},
        использований: {created.invite.max_uses}.
      </p>
    </div>
  );
}
