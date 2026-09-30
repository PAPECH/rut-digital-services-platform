import { useCallback, useEffect, useMemo, useState } from "react";

import type { ApiError } from "@/api/client";
import type {
  AdminForm,
  FormCreate,
  FormDraft,
} from "@/entities/form/model/types";
import { formApi } from "@/features/form-management/api/formApi";

function errorMessage(error: unknown): string {
  const apiError = error as ApiError;
  if (apiError.code === "form_draft_revision_conflict")
    return "Черновик изменён другим редактором. Обновите данные.";
  return error instanceof Error
    ? error.message
    : "Не удалось выполнить операцию";
}

export function useFormBuilder() {
  const [forms, setForms] = useState<AdminForm[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [draft, setDraft] = useState<FormDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<
    "save" | "publish" | "reorder" | "patch" | "import" | null
  >(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const active = useMemo(
    () => forms.find((form) => form.id === activeId) ?? null,
    [forms, activeId],
  );

  const load = useCallback(
    async (preferredId?: number) => {
      setLoading(true);
      setError(null);
      try {
        const list = await formApi.list();
        setForms(list);
        const id = preferredId ?? activeId ?? list[0]?.id ?? null;
        setActiveId(id);
        const source = list.find((form) => form.id === id)?.draft;
        setDraft(source ? structuredClone(source) : null);
      } catch (error) {
        setError(errorMessage(error));
      } finally {
        setLoading(false);
      }
    },
    [activeId],
  );

  useEffect(() => {
    void load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */
  }, []);

  const select = (form: AdminForm) => {
    setActiveId(form.id);
    setDraft(structuredClone(form.draft));
    setError(null);
    setNotice(null);
  };
  const create = async (payload: FormCreate) => {
    const created = await formApi.create(payload);
    setForms((rows) => [...rows, created].sort((a, b) => a.order - b.order));
    select(created);
    return created;
  };
  const save = async () => {
    if (!draft) return;
    setBusy("save");
    setError(null);
    setNotice(null);
    try {
      const saved = await formApi.saveDraft(draft);
      setDraft(saved);
      setForms((rows) =>
        rows.map((form) =>
          form.id === saved.form_id ? { ...form, draft: saved } : form,
        ),
      );
      setNotice("Черновик сохранён");
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(null);
    }
  };
  const publish = async () => {
    if (!draft || !active) return;
    setBusy("publish");
    setError(null);
    setNotice(null);
    try {
      const version = await formApi.publish(active.id, draft.revision);
      setForms((rows) =>
        rows.map((form) =>
          form.id === active.id
            ? {
                ...form,
                published_version_id: version.version_id,
                last_published_revision: draft.revision,
              }
            : form,
        ),
      );
      setNotice(`Опубликована версия ${version.version}`);
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(null);
    }
  };
  const patch = async (
    payload: Partial<
      Pick<AdminForm, "is_active" | "show_in_catalog" | "is_archived">
    >,
  ) => {
    if (!active) return;
    setBusy("patch");
    setError(null);
    try {
      const updated = await formApi.patch(active.id, payload);
      setForms((rows) =>
        rows.map((form) => (form.id === updated.id ? updated : form)),
      );
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(null);
    }
  };
  const move = async (formId: number, direction: -1 | 1) => {
    const index = forms.findIndex((form) => form.id === formId);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= forms.length) return;
    const reordered = [...forms];
    [reordered[index], reordered[target]] = [
      reordered[target],
      reordered[index],
    ];
    setForms(reordered);
    setBusy("reorder");
    try {
      setForms(await formApi.reorder(reordered.map((form) => form.id)));
    } catch (error) {
      setForms(forms);
      setError(errorMessage(error));
    } finally {
      setBusy(null);
    }
  };
  const importSharedDraft = async (sourceFormId: number, slug: string) => {
    setBusy("import");
    setError(null);
    setNotice(null);
    try {
      const created = await formApi.importSharedDraft(
        sourceFormId,
        slug,
        forms.length,
      );
      setForms((rows) => [...rows, created].sort((a, b) => a.order - b.order));
      select(created);
      setNotice("Общий черновик формы скопирован в текущий бот");
      return created;
    } catch (error) {
      setError(errorMessage(error));
      throw error;
    } finally {
      setBusy(null);
    }
  };
  return {
    forms,
    active,
    draft,
    setDraft,
    loading,
    busy,
    error,
    notice,
    select,
    create,
    save,
    publish,
    patch,
    move,
    importSharedDraft,
    reload: () => load(activeId ?? undefined),
  };
}
