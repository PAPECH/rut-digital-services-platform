import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { getSelectedBotSlug } from "@/shared/tenant/selectedBotStorage";

const MINIAPP_URL = import.meta.env.VITE_MINIAPP_URL || "http://localhost:5174";

interface PreviewTokenResponse {
  token: string;
  expires_at: string;
}

/**
 * Renders the real mini-app, not a hand-maintained approximation — embeds
 * `frontend-miniapp`'s `/preview/:token` route in an iframe so the same components/CSS users see
 * are what the admin sees. Reflects the last *saved* draft, not unsaved edits, matching the
 * existing explicit-save editing model (see `useContentBuilder`'s `save`).
 */
export function ContentPreviewFrame({
  categoryId,
  revision,
}: {
  categoryId: number;
  revision: number;
}) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setSrc(null);
    setError(null);
    api
      .post<PreviewTokenResponse>(`/content/admin/categories/${categoryId}/preview-token`)
      .then((response) => {
        if (!active) return;
        const url = new URL(`${MINIAPP_URL}/preview/${response.token}`);
        url.searchParams.set("bot", getSelectedBotSlug());
        setSrc(url.toString());
      })
      .catch((reason) => {
        if (active) setError((reason as Error).message);
      });
    return () => {
      active = false;
    };
  }, [categoryId, revision]);

  return (
    <div className="content-phone-preview">
      <div className="content-phone-preview__bar">
        <span>Предпросмотр</span>
        <span>•••</span>
      </div>
      {error ? (
        <div className="content-preview-placeholder form-error">{error}</div>
      ) : src ? (
        <iframe
          key={src}
          src={src}
          className="content-phone-preview__frame"
          title="Предпросмотр страницы"
        />
      ) : (
        <div className="content-preview-placeholder">Загрузка предпросмотра…</div>
      )}
    </div>
  );
}
