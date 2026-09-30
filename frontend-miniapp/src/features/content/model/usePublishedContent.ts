import { useContentCatalog } from "@/features/content/model/ContentCatalogProvider";

export function usePublishedContent(slug: string | undefined) {
  const { bySlug, loading, error } = useContentCatalog();
  const content = slug ? (bySlug.get(slug) ?? null) : null;
  return {
    content,
    loading,
    error: !slug ? "Категория не указана" : error,
  };
}
