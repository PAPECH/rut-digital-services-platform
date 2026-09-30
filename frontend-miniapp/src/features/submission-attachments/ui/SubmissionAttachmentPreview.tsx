import { useEffect, useState } from "react";

import type { SubmissionAttachment } from "@/api/types";
import { fetchSubmissionAttachment } from "@/features/submission-attachments/api/submissionAttachmentApi";
import { useI18n } from "@/i18n";

export function SubmissionAttachmentPreview({
  item,
  onClose,
}: {
  item: SubmissionAttachment;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    fetchSubmissionAttachment(item.preview_url)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {
        if (active) setError(true);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [item.id, item.preview_url]);

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  return (
    <div
      className="history-file-preview"
      role="dialog"
      aria-modal="true"
      aria-label={`${t("history:files:preview")}: ${item.name}`}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section className="history-file-preview__dialog">
        <header>
          <div>
            <strong>{item.name}</strong>
            <span>{item.mime}</span>
          </div>
          <button
            type="button"
            aria-label={t("history:files:close")}
            onClick={onClose}
          >
            ×
          </button>
        </header>
        <div className="history-file-preview__body">
          {!url && !error ? <span>{t("history:files:loading")}</span> : null}
          {error ? <span className="history-files-error">{t("history:files:open_error")}</span> : null}
          {url && item.mime.startsWith("image/") ? (
            <img src={url} alt={item.name} />
          ) : null}
          {url && item.mime === "application/pdf" ? (
            <iframe src={url} title={item.name} />
          ) : null}
        </div>
      </section>
    </div>
  );
}
