import { useCallback, useEffect, useState } from "react";

import type { ApiError } from "@/api/client";
import type { AdminTestDetail, TestDraft } from "@/entities/form-test/model/types";
import { formTestApi } from "@/features/form-test-management/api/formTestApi";

function errorMessage(error: unknown): string {
  const apiError = error as ApiError;
  if (apiError.code === "test_draft_revision_conflict") {
    return "Черновик изменён другим редактором. Обновите данные и повторите.";
  }
  if (apiError.code === "invalid_import_file") {
    return apiError.message;
  }
  return error instanceof Error ? error.message : "Не удалось выполнить операцию";
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function useTestDraftBuilder(testId: number | null, onPublished?: () => void) {
  const [draft, setDraft] = useState<TestDraft | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<"save" | "publish" | "export" | "import" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (testId == null) {
      setDraft(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setDraft(await formTestApi.getDraft(testId));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [testId]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    if (!draft || testId == null) return;
    setBusy("save");
    setError(null);
    setNotice(null);
    try {
      const saved = await formTestApi.saveDraft(testId, draft);
      setDraft(saved);
      setNotice("Черновик сохранён");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const publish = async (): Promise<AdminTestDetail | null> => {
    if (!draft || testId == null) return null;
    setBusy("publish");
    setError(null);
    setNotice(null);
    try {
      const published = await formTestApi.publish(testId, draft.revision);
      setNotice("Тест опубликован");
      onPublished?.();
      return published;
    } catch (err) {
      setError(errorMessage(err));
      return null;
    } finally {
      setBusy(null);
    }
  };

  const exportXlsx = async () => {
    if (testId == null) return;
    setBusy("export");
    setError(null);
    try {
      const blob = await formTestApi.exportDraftBlob(testId);
      downloadBlob(blob, `test-${testId}-draft.xlsx`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const exportVersionXlsx = async (versionId: number) => {
    if (testId == null) return;
    setBusy("export");
    setError(null);
    try {
      const blob = await formTestApi.exportVersionBlob(testId, versionId);
      downloadBlob(blob, `test-${testId}-version-${versionId}.xlsx`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const importXlsx = async (file: File) => {
    if (!draft || testId == null) return;
    setBusy("import");
    setError(null);
    setNotice(null);
    try {
      const parsed = await formTestApi.importDraftXlsx(testId, file);
      setDraft({
        ...draft,
        name: parsed.name,
        intro_text: parsed.intro_text,
        test_schema: parsed.test_schema,
      });
      setNotice("Файл загружен в редактор — проверьте и сохраните черновик");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  return {
    draft,
    setDraft,
    loading,
    busy,
    error,
    notice,
    save,
    publish,
    exportXlsx,
    exportVersionXlsx,
    importXlsx,
    reload: load,
  };
}
