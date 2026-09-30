import { isShortcutCategory, type AdminContentCategory } from "@/entities/content/model/types";

export function collectDescendantCategoryIds(
  categories: AdminContentCategory[],
  categoryId: number,
): Set<number> {
  const descendants = new Set<number>();
  const pending = [categoryId];

  while (pending.length) {
    const parentId = pending.pop();
    if (parentId === undefined) continue;
    for (const category of categories) {
      if (category.parent_id !== parentId || descendants.has(category.id)) continue;
      descendants.add(category.id);
      pending.push(category.id);
    }
  }

  return descendants;
}

/** Valid reparent targets for an existing category: not itself, not one of its own descendants
 * (would create a cycle), and not a capability shortcut -- a shortcut can never have children. */
export function availableCategoryParents(
  categories: AdminContentCategory[],
  categoryId: number,
): AdminContentCategory[] {
  const excluded = collectDescendantCategoryIds(categories, categoryId);
  excluded.add(categoryId);
  return categories.filter((category) => !excluded.has(category.id) && !isShortcutCategory(category));
}

/** Valid parent options when creating a brand new category or shortcut -- every existing
 * category except capability shortcuts, which can never have children. */
export function availableNewCategoryParents(categories: AdminContentCategory[]): AdminContentCategory[] {
  return categories.filter((category) => !isShortcutCategory(category));
}
