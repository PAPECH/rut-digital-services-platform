import { useContentCatalog } from "@/features/content/model/ContentCatalogProvider";

export function useContentCategories() {
  const { categories, loading, error, reload } = useContentCatalog();
  return { categories, loading, error, reload };
}
