import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import type {
  AdminTestDetail,
  AdminTestSummary,
  TestCreate,
} from "@/entities/form-test/model/types";
import { formTestApi } from "@/features/form-test-management/api/formTestApi";

function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "Не удалось загрузить тесты";
}

export function useFormTests() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tests, setTests] = useState<AdminTestSummary[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [detail, setDetail] = useState<AdminTestDetail | null>(null);
  // Bumped by `reload()` to force the detail-fetch effect below to re-run even though `activeId`
  // itself hasn't changed -- e.g. after publishing the currently-selected test, whose
  // `published_version_id`/`is_active` the effect would otherwise keep serving stale (it only
  // re-runs on an `activeId` change, but publishing doesn't change which test is selected).
  const [detailVersion, setDetailVersion] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const active = useMemo(
    () => tests.find((test) => test.id === activeId) ?? null,
    [tests, activeId],
  );

  const loadList = useCallback(async (preferredId?: number) => {
    setLoading(true);
    setError(null);
    try {
      const list = await formTestApi.list();
      setTests(list);
      setActiveId((current) => preferredId ?? current ?? list[0]?.id ?? null);
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Deep link from a content editor's `test_action` block (Task 070): `/form-tests?testId=9`
    // pre-selects that test, then the param is dropped so it doesn't stick around after the
    // admin picks a different test.
    const requestedTestId = Number(searchParams.get("testId")) || undefined;
    void loadList(requestedTestId);
    if (requestedTestId) {
      const next = new URLSearchParams(searchParams);
      next.delete("testId");
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadList]);

  useEffect(() => {
    if (activeId == null) {
      setDetail(null);
      return;
    }
    let cancelled = false;
    void formTestApi.detail(activeId).then(
      (result) => {
        if (!cancelled) setDetail(result);
      },
      (error: unknown) => {
        if (!cancelled) setError(errorMessage(error));
      },
    );
    return () => {
      cancelled = true;
    };
  }, [activeId, detailVersion]);

  const selectTest = useCallback((testId: number) => {
    setActiveId(testId);
  }, []);

  const toggle = useCallback(
    async (
      testId: number,
      payload: Partial<Pick<AdminTestSummary, "is_active" | "is_archived">>,
    ) => {
      setBusy(true);
      setError(null);
      try {
        const updated = await formTestApi.updateTest(testId, payload);
        setTests((rows) =>
          rows.map((row) => (row.id === testId ? updated : row)),
        );
        setDetail((current) =>
          current && current.id === testId ? { ...current, ...updated } : current,
        );
      } catch (error) {
        setError(errorMessage(error));
      } finally {
        setBusy(false);
      }
    },
    [],
  );

  const create = useCallback(
    async (payload: TestCreate) => {
      const created = await formTestApi.create(payload);
      await loadList(created.id);
      return created;
    },
    [loadList],
  );

  const move = useCallback(
    async (testId: number, direction: -1 | 1) => {
      const index = tests.findIndex((test) => test.id === testId);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= tests.length) return;
      const reordered = [...tests];
      [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
      setTests(reordered);
      setBusy(true);
      try {
        setTests(await formTestApi.reorder(reordered.map((test) => test.id)));
      } catch (error) {
        setTests(tests);
        setError(errorMessage(error));
      } finally {
        setBusy(false);
      }
    },
    [tests],
  );

  const reload = useCallback(() => {
    void loadList(activeId ?? undefined);
    // Re-run the detail-fetch effect for the still-selected test (see `detailVersion` above) --
    // `loadList` alone only refreshes `tests`/`active`, which `FormTestOverview`'s status toggle
    // does not read from.
    setDetailVersion((v) => v + 1);
  }, [loadList, activeId]);

  return {
    tests,
    active,
    detail,
    loading,
    busy,
    error,
    selectTest,
    toggle,
    create,
    move,
    reload,
  };
}
