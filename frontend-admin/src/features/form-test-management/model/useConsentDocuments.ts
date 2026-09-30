import { useCallback, useEffect, useState } from "react";

import type {
  ConsentDocumentDetail,
  ConsentDocumentSave,
  ConsentDocumentSummary,
} from "@/entities/form-test/model/types";
import { formTestApi } from "@/features/form-test-management/api/formTestApi";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Не удалось выполнить операцию";
}

export function useConsentDocuments() {
  const [documents, setDocuments] = useState<ConsentDocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDocuments(await formTestApi.listConsentDocuments());
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const create = useCallback(
    async (payload: ConsentDocumentSave): Promise<ConsentDocumentDetail | null> => {
      setBusy(true);
      setError(null);
      try {
        const created = await formTestApi.createConsentDocument(payload);
        await load();
        return created;
      } catch (err) {
        setError(errorMessage(err));
        return null;
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  const update = useCallback(
    async (documentId: number, payload: ConsentDocumentSave): Promise<boolean> => {
      setBusy(true);
      setError(null);
      try {
        await formTestApi.updateConsentDocument(documentId, payload);
        await load();
        return true;
      } catch (err) {
        setError(errorMessage(err));
        return false;
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  const remove = useCallback(
    async (documentId: number): Promise<boolean> => {
      setBusy(true);
      setError(null);
      try {
        await formTestApi.deleteConsentDocument(documentId);
        await load();
        return true;
      } catch (err) {
        setError(errorMessage(err));
        return false;
      } finally {
        setBusy(false);
      }
    },
    [load],
  );

  return { documents, loading, busy, error, reload: load, create, update, remove };
}
