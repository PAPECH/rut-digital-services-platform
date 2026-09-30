import { useCallback, useEffect, useMemo, useState } from "react";

import type { ApiError } from "@/api/client";
import type {
  AdminContentCategory,
  ContentCategoryCreate,
  ContentDraft,
  ContentFormDependencyResolution,
  ContentShortcutCardPatch,
} from "@/entities/content/model/types";
import type { ContentIconName } from "@/entities/content/model/contentIcons";
import { contentApi } from "@/features/content-management/api/contentApi";

function errorMessage(error: unknown): string {
  const apiError = error as ApiError;
  if (apiError.code === "draft_revision_conflict") {
    return "Черновик уже изменил другой редактор. Обновите данные перед продолжением.";
  }
  return error instanceof Error
    ? error.message
    : "Не удалось выполнить операцию";
}

export function useContentBuilder() {
  const [categories, setCategories] = useState<AdminContentCategory[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [draft, setDraft] = useState<ContentDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<
    "save" | "publish" | "reorder" | "patch" | "import" | null
  >(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const active = useMemo(
    () => categories.find((category) => category.id === activeId) ?? null,
    [activeId, categories],
  );

  const load = useCallback(
    async (preferredId?: number) => {
      setLoading(true);
      setError(null);
      try {
        const list = await contentApi.list();
        setCategories(list);
        const nextId = preferredId ?? activeId ?? list[0]?.id ?? null;
        setActiveId(nextId);
        setDraft(
          list.find((category) => category.id === nextId)?.draft ?? null,
        );
      } catch (loadError) {
        setError(errorMessage(loadError));
      } finally {
        setLoading(false);
      }
    },
    [activeId],
  );

  useEffect(() => {
    void load();
    // The initial request intentionally follows the currently selected bot only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const select = (category: AdminContentCategory) => {
    setActiveId(category.id);
    setDraft(structuredClone(category.draft));
    setError(null);
    setNotice(null);
  };

  const create = async (payload: ContentCategoryCreate) => {
    setError(null);
    const created = await contentApi.create(payload);
    setCategories((current) =>
      [...current, created].sort((a, b) => a.order - b.order),
    );
    select(created);
    return created;
  };

  const save = async () => {
    if (!draft) return;
    setBusy("save");
    setError(null);
    setNotice(null);
    try {
      const saved = await contentApi.saveDraft(draft);
      setDraft(saved);
      setCategories((current) =>
        current.map((category) =>
          category.id === saved.category_id
            ? { ...category, draft: saved }
            : category,
        ),
      );
      setNotice("Черновик сохранён");
    } catch (saveError) {
      setError(errorMessage(saveError));
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
      const published = await contentApi.publish(active.id, draft.revision);
      setCategories((current) =>
        current.map((category) =>
          category.id === active.id
            ? {
                ...category,
                published_version_id: published.version_id,
                last_published_revision: draft.revision,
              }
            : category,
        ),
      );
      setNotice(`Опубликована версия ${published.version}`);
    } catch (publishError) {
      setError(errorMessage(publishError));
    } finally {
      setBusy(null);
    }
  };

  const patchVisibility = async (
    category: AdminContentCategory,
    isActive: boolean,
  ) => {
    setBusy("patch");
    setError(null);
    try {
      const updated = await contentApi.patch(category.id, {
        is_active: isActive,
      });
      setCategories((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
    } catch (patchError) {
      setError(errorMessage(patchError));
    } finally {
      setBusy(null);
    }
  };

  const patchIcon = async (
    category: AdminContentCategory,
    icon: ContentIconName,
  ) => {
    setBusy("patch");
    setError(null);
    try {
      const updated = await contentApi.patch(category.id, { icon });
      setCategories((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setNotice("Иконка категории обновлена");
    } catch (patchError) {
      setError(errorMessage(patchError));
    } finally {
      setBusy(null);
    }
  };

  const patchShortcutCard = async (
    categoryId: number,
    payload: ContentShortcutCardPatch,
  ) => {
    setBusy("patch");
    setError(null);
    setNotice(null);
    try {
      const updated = await contentApi.patch(categoryId, payload);
      setCategories((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setNotice("Ссылка на возможность обновлена");
      return updated;
    } catch (patchError) {
      setError(errorMessage(patchError));
      throw patchError;
    } finally {
      setBusy(null);
    }
  };

  const patchParent = async (
    category: AdminContentCategory,
    parentId: number | null,
  ) => {
    setBusy("patch");
    setError(null);
    setNotice(null);
    try {
      const updated = await contentApi.patch(category.id, {
        parent_id: parentId,
      });
      setCategories((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setNotice(
        parentId === null
          ? "Категория перенесена в корень"
          : "Родительская категория обновлена",
      );
    } catch (patchError) {
      setError(errorMessage(patchError));
    } finally {
      setBusy(null);
    }
  };

  const move = async (categoryId: number, direction: -1 | 1) => {
    const category = categories.find((item) => item.id === categoryId);
    if (!category) return;
    const siblings = categories
      .filter((item) => item.parent_id === category.parent_id && !item.is_home)
      .sort((a, b) => a.order - b.order);
    const siblingIndex = siblings.findIndex((item) => item.id === categoryId);
    const siblingTarget = siblingIndex + direction;
    if (siblingIndex < 0 || siblingTarget < 0 || siblingTarget >= siblings.length) return;
    const index = categories.findIndex((item) => item.id === siblings[siblingIndex].id);
    const target = categories.findIndex((item) => item.id === siblings[siblingTarget].id);
    const reordered = [...categories];
    [reordered[index], reordered[target]] = [
      reordered[target],
      reordered[index],
    ];
    setCategories(reordered);
    setBusy("reorder");
    try {
      setCategories(
        await contentApi.reorder(reordered.map((category) => category.id)),
      );
    } catch (reorderError) {
      setCategories(categories);
      setError(errorMessage(reorderError));
    } finally {
      setBusy(null);
    }
  };

  const importSharedDraft = async (
    sourceCategoryId: number,
    slug: string,
    resolutions: ContentFormDependencyResolution[],
    parentId: number | null = null,
  ) => {
    setBusy("import");
    setError(null);
    setNotice(null);
    try {
      const order = categories.filter(
        (category) => category.parent_id === parentId,
      ).length;
      const imported = await contentApi.importSharedDraft(
        sourceCategoryId,
        slug,
        parentId,
        order,
        resolutions,
      );
      const created = imported.category;
      setCategories((current) => [...current, created]);
      select(created);
      const copiedForms = imported.dependencies.filter(
        (item) => item.action === "copy_shared",
      ).length;
      setNotice(
        copiedForms
          ? `Категория и черновики форм (${copiedForms}) скопированы. Опубликуйте и активируйте формы.`
          : "Общий черновик категории скопирован в текущий бот",
      );
      return imported;
    } catch (importError) {
      setError(errorMessage(importError));
      throw importError;
    } finally {
      setBusy(null);
    }
  };

  return {
    categories,
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
    patchVisibility,
    patchIcon,
    patchParent,
    patchShortcutCard,
    move,
    importSharedDraft,
    reload: () => load(activeId ?? undefined),
  };
}
