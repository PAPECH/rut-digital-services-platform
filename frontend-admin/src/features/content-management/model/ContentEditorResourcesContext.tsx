import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import type {
  AdminContentCategory,
  ContentAttachmentOption,
  ContentFormOption,
  ContentTestOption,
} from "@/entities/content/model/types";
import { contentApi } from "@/features/content-management/api/contentApi";

interface ContentEditorResources {
  forms: ContentFormOption[];
  tests: ContentTestOption[];
  attachments: ContentAttachmentOption[];
  /** Excludes the home-screen singleton -- it is never a valid category_grid parent target. */
  categories: AdminContentCategory[];
  loading: boolean;
  error: string | null;
  registerAttachment: (attachment: ContentAttachmentOption) => void;
}

const Context = createContext<ContentEditorResources | null>(null);

export function ContentEditorResourcesProvider({ children }: { children: ReactNode }) {
  const [forms, setForms] = useState<ContentFormOption[]>([]);
  const [tests, setTests] = useState<ContentTestOption[]>([]);
  const [attachments, setAttachments] = useState<ContentAttachmentOption[]>([]);
  const [categories, setCategories] = useState<AdminContentCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    // A bounded lookup list, not the picker's own paginated/searchable fetch (see
    // features/content-files) -- this only needs to resolve mime/url/name for an
    // already-picked attachment_id so block editors can show a thumbnail without a
    // second round-trip per row.
    Promise.all([
      contentApi.listForms(),
      contentApi.listTests(),
      contentApi.listAttachments({ limit: 200 }),
      contentApi.list(),
    ])
      .then(([nextForms, nextTests, attachmentPage, nextCategories]) => {
        if (!active) return;
        setForms(nextForms);
        setTests(nextTests);
        setAttachments(attachmentPage.items);
        setCategories(nextCategories.filter((category) => !category.is_home));
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Не удалось загрузить справочники");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const registerAttachment = useCallback((attachment: ContentAttachmentOption) => {
    setAttachments((current) => [attachment, ...current.filter((item) => item.id !== attachment.id)]);
  }, []);
  const value = useMemo(
    () => ({ forms, tests, attachments, categories, loading, error, registerAttachment }),
    [attachments, categories, error, forms, tests, loading, registerAttachment],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useContentEditorResources(): ContentEditorResources {
  const value = useContext(Context);
  if (!value) throw new Error("ContentEditorResourcesProvider is missing");
  return value;
}
