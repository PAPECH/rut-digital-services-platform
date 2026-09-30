import { useEffect, useState } from "react";

import type { SubmissionAttachment } from "@/api/types";
import { Icon } from "@/components/Icon";
import { fetchSubmissionAttachment } from "@/features/submission-attachments/api/submissionAttachmentApi";
import { SubmissionAttachmentPreview } from "@/features/submission-attachments/ui/SubmissionAttachmentPreview";
import { useI18n } from "@/i18n";
import { formatBytes, isPreviewableMime } from "@/lib/files";

export function SubmissionAttachmentItem({
  item,
}: {
  item: SubmissionAttachment;
}) {
  const { t } = useI18n();
  const [thumbnail, setThumbnail] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [downloadError, setDownloadError] = useState(false);

  useEffect(() => {
    if (!item.mime.startsWith("image/")) return;
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
    setDownloadError(false);
    try {
      const blob = await fetchSubmissionAttachment(item.download_url);
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = item.name;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    } catch {
      setDownloadError(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="history-attachment">
      {thumbnail ? (
        <button
          className="history-attachment__thumbnail"
          type="button"
          onClick={() => setPreviewOpen(true)}
          aria-label={`${t("history:files:preview")}: ${item.name}`}
        >
          <img src={thumbnail} alt="" />
        </button>
      ) : (
        <span className="history-attachment__icon"><Icon.Paperclip /></span>
      )}
      <div className="history-attachment__meta">
        <strong>{item.name}</strong>
        <span>{formatBytes(item.size_bytes)}</span>
      </div>
      <div className="history-attachment__actions">
        {isPreviewableMime(item.mime) ? (
          <button type="button" onClick={() => setPreviewOpen(true)}>
            {t("history:files:preview")}
          </button>
        ) : null}
        <button type="button" disabled={busy} onClick={() => void download()}>
          <span className="history-attachment__action-icon"><Icon.Download /></span>
          {t("history:files:download")}
        </button>
      </div>
      {downloadError ? (
        <span className="history-files-state history-files-error">
          {t("history:files:open_error")}
        </span>
      ) : null}
      {previewOpen ? (
        <SubmissionAttachmentPreview
          item={item}
          onClose={() => setPreviewOpen(false)}
        />
      ) : null}
    </div>
  );
}
