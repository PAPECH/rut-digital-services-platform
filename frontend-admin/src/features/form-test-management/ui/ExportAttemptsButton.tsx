import { useState } from "react";

import { formTestApi } from "@/features/form-test-management/api/formTestApi";
import type { AttemptsValueMode } from "@/features/form-test-management/model/useAttemptsDisplayPrefs";

async function withObjectUrl(blob: Blob, use: (url: string) => void): Promise<void> {
  const url = URL.createObjectURL(blob);
  try {
    use(url);
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function ExportAttemptsButton({
  testId,
  valueMode,
}: {
  testId: number;
  valueMode: AttemptsValueMode;
}) {
  const [busy, setBusy] = useState(false);

  const download = async () => {
    setBusy(true);
    try {
      const blob = await formTestApi.exportAttemptsBlob(testId, valueMode);
      await withObjectUrl(blob, (url) => {
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `test-${testId}-attempts.xlsx`;
        anchor.click();
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      className="btn btn-secondary btn-sm"
      disabled={busy}
      onClick={() => void download()}
    >
      {busy ? "Готовим файл…" : "Экспорт в Excel"}
    </button>
  );
}
