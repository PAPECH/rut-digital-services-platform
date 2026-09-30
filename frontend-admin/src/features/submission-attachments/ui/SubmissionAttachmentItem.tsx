import { useEffect, useState } from "react";

import type { SubmissionAttachment } from "@/api/types";
import { formatBytes } from "@/api/files";
import { Icon } from "@/components/Icon";
import { fetchSubmissionAttachment } from "@/features/submission-attachments/api/submissionAttachmentApi";
import { SubmissionAttachmentPreview } from "@/features/submission-attachments/ui/SubmissionAttachmentPreview";

function isImage(mime: string): boolean {
  return mime.startsWith("image/");
}

async function withObjectUrl(blob: Blob, action: (url: string) => void) {
  const url = URL.createObjectURL(blob);
  action(url);
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export function SubmissionAttachmentItem({ item }: { item: SubmissionAttachment }) {
  const [thumbnail, setThumbnail] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);

  useEffect(() => {
    if (!isImage(item.mime)) return;
    let active = true;
    let objectUrl: string | null = null;
    fetchSubmissionAttachment(item.preview_url)
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setThumbnail(objectUrl);
      })
      .catch(() => undefined);
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [item.id, item.mime, item.preview_url]);

  const download = async () => {
    setBusy(true);
    try {
      const blob = await fetchSubmissionAttachment(item.download_url);
      await withObjectUrl(blob, (url) => {
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = item.name;
        anchor.click();
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="submission-attachment">
      {thumbnail ? (
        <button
          className="submission-attachment__preview"
          type="button"
          aria-label={`Открыть предпросмотр ${item.name}`}
          onClick={() => setPreviewOpen(true)}
        >
          <img src={thumbnail} alt={item.name} />
        </button>
      ) : (
        <span className="submission-attachment__icon"><Icon.Paperclip /></span>
      )}
      <div className="submission-attachment__meta">
        <strong>{item.name}</strong>
        <span>{item.mime} · {formatBytes(item.size_bytes)}</span>
      </div>
      <div className="submission-attachment__actions">
        {(isImage(item.mime) || item.mime === "application/pdf") ? (
          <button
            className="btn btn-ghost btn-sm"
            type="button"
            disabled={busy}
            onClick={() => setPreviewOpen(true)}
          >
            Предпросмотр
          </button>
        ) : null}
        <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => void download()}>
          <span className="ico"><Icon.Download /></span>
          Скачать
        </button>
      </div>
      {previewOpen ? (
        <SubmissionAttachmentPreview
          item={item}
          onClose={() => setPreviewOpen(false)}
        />
      ) : null}
    </div>
  );
}
