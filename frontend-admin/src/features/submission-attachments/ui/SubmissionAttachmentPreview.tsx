import { useEffect, useState } from "react";

import type { SubmissionAttachment } from "@/api/types";
import { fetchSubmissionAttachment } from "@/features/submission-attachments/api/submissionAttachmentApi";

function isImage(mime: string): boolean {
  return mime.startsWith("image/");
}

export function SubmissionAttachmentPreview({
  item,
  onClose,
}: {
  item: SubmissionAttachment;
  onClose: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;
    fetchSubmissionAttachment(item.preview_url)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Не удалось открыть файл",
          );
        }
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [item.id, item.preview_url]);

  return (
    <div
      className="submission-preview"
      role="dialog"
      aria-modal="true"
      aria-label={`Предпросмотр ${item.name}`}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section className="submission-preview__dialog">
        <header className="submission-preview__header">
          <div>
            <strong>{item.name}</strong>
            <span>{item.mime}</span>
          </div>
          <button
            className="btn btn-ghost btn-icon"
            type="button"
            aria-label="Закрыть предпросмотр"
            onClick={onClose}
          >
            ×
          </button>
        </header>
        <div className="submission-preview__body">
          {!url && !error ? <span>Загружаем файл…</span> : null}
          {error ? <span className="submission-preview__error">{error}</span> : null}
          {url && isImage(item.mime) ? (
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
