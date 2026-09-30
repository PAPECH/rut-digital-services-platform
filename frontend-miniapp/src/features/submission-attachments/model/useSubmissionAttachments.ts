import { useEffect, useMemo, useState } from "react";

import type { SubmissionAttachment } from "@/api/types";
import { listSubmissionAttachments } from "@/features/submission-attachments/api/submissionAttachmentApi";

export function useSubmissionAttachments(submissionId: number) {
  const [items, setItems] = useState<SubmissionAttachment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setItems([]);
    setLoading(true);
    setError(null);
    listSubmissionAttachments(submissionId)
      .then((result) => {
        if (active) setItems(result);
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : "Не удалось загрузить файлы");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [submissionId]);

  const byField = useMemo(() => {
    const result = new Map<string, SubmissionAttachment[]>();
    for (const item of items) {
      result.set(item.field_key, [...(result.get(item.field_key) ?? []), item]);
    }
    return result;
  }, [items]);

  return { byField, loading, error };
}
