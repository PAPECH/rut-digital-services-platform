import { useCallback, useEffect, useState } from "react";

import type {
  AdminAttemptSummary,
  TestAttemptStatus,
} from "@/entities/form-test/model/types";
import { formTestApi } from "@/features/form-test-management/api/formTestApi";

export function useTestAttempts(testId: number | null) {
  const [attempts, setAttempts] = useState<AdminAttemptSummary[]>([]);
  const [statusFilter, setStatusFilter] = useState<TestAttemptStatus | "all">(
    "all",
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (testId == null) {
      setAttempts([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const rows = await formTestApi.listAttempts(
        testId,
        statusFilter === "all" ? undefined : statusFilter,
      );
      setAttempts(rows);
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "Не удалось загрузить попытки",
      );
    } finally {
      setLoading(false);
    }
  }, [testId, statusFilter]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { attempts, statusFilter, setStatusFilter, loading, error, reload };
}
