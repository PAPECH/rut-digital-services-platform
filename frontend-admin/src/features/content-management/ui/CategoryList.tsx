import { useEffect, useState } from "react";

import { api } from "@/api/client";
import { isShortcutCategory, type AdminContentCategory } from "@/entities/content/model/types";
import { ContentIcon } from "@/entities/content/ui/ContentIcon";

interface CategoryListProps {
  categories: AdminContentCategory[];
  activeId: number | null;
  reordering: boolean;
  onSelect: (category: AdminContentCategory) => void;
  onMove: (categoryId: number, direction: -1 | 1) => void;
  onAddChild: (categoryId: number) => void;
  onAddShortcut: (categoryId: number) => void;
}

/** A shortcut row shows a degraded badge once its target capability is no longer in the
 * currently enabled set -- distinct from an ordinary category with no published content, since
 * those are different problems (see Task 044's admin section). */
function useEnabledCapabilityKeys(): Set<string> {
  const [keys, setKeys] = useState<Set<string>>(new Set());
  useEffect(() => {
    let active = true;
    api
      .get<{ capabilities: Array<{ key: string }> }>("/manifest")
      .then((result) => {
        if (active) setKeys(new Set((result.capabilities || []).map((item) => item.key)));
      })
      .catch(() => {
        // Leave the set empty on failure -- every shortcut shows as degraded rather than
        // silently pretending everything is fine when the manifest couldn't be checked.
      });
    return () => {
      active = false;
    };
  }, []);
  return keys;
}

export function CategoryList(props: CategoryListProps) {
  const { categories, activeId } = props;
  const enabledCapabilityKeys = useEnabledCapabilityKeys();
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  // Reveal a nested category when it becomes active (e.g. right after creating it under a
  // collapsed parent) instead of leaving the selection hidden inside a closed branch.
  useEffect(() => {
    if (activeId === null) return;
    setExpandedIds((current) => {
      const next = new Set(current);
      let changed = false;
      let cursor = categories.find((category) => category.id === activeId);
      while (cursor && cursor.parent_id !== null) {
        if (!next.has(cursor.parent_id)) {
          next.add(cursor.parent_id);
          changed = true;
        }
        cursor = categories.find((category) => category.id === cursor!.parent_id);
      }
      return changed ? next : current;
    });
  }, [activeId, categories]);

  const toggleExpanded = (categoryId: number) => {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(categoryId)) next.delete(categoryId);
      else next.add(categoryId);
      return next;
    });
  };

  if (!categories.length) {
    return (
      <div className="content-empty-state">
        <strong>Категорий пока нет</strong>
        <span>Создайте первую карточку для мини-приложения.</span>
      </div>
    );
  }
  const ids = new Set(categories.map((category) => category.id));
  const roots = categories
    .filter((category) => category.parent_id === null || !ids.has(category.parent_id))
    .sort((a, b) => a.order - b.order);
  return (
    <div className="content-category-list">
      {roots.map((category, index) => (
        <CategoryRow
          {...props}
          enabledCapabilityKeys={enabledCapabilityKeys}
          expandedIds={expandedIds}
          onToggleExpand={toggleExpanded}
          category={category}
          depth={0}
          first={index === 0}
          last={index === roots.length - 1}
          key={category.id}
        />
      ))}
    </div>
  );
}

function CategoryRow({
  category,
  categories,
  activeId,
  reordering,
  onSelect,
  onMove,
  onAddChild,
  onAddShortcut,
  enabledCapabilityKeys,
  expandedIds,
  onToggleExpand,
  depth,
  first,
  last,
}: CategoryListProps & {
  enabledCapabilityKeys: Set<string>;
  expandedIds: Set<number>;
  onToggleExpand: (categoryId: number) => void;
  category: AdminContentCategory;
  depth: number;
  first: boolean;
  last: boolean;
}) {
  const children = categories
    .filter((item) => item.parent_id === category.id)
    .sort((a, b) => a.order - b.order);
  const hasChildren = children.length > 0;
  const isExpanded = expandedIds.has(category.id);
  const isShortcut = isShortcutCategory(category);
  const isDegraded = isShortcut && !enabledCapabilityKeys.has(category.capability_key as string);
  const title = category.title ?? category.draft?.title ?? category.slug;
  const handleSelect = () => {
    onSelect(category);
    if (hasChildren) onToggleExpand(category.id);
  };
  return (
    <div className="content-category-tree-node">
      <article
        className={`content-category-row ${activeId === category.id ? "active" : ""}`}
      >
        <button type="button" className="content-category-row__select" onClick={handleSelect}>
          {hasChildren ? (
            <span
              className={`content-category-toggle ${isExpanded ? "content-category-toggle--expanded" : ""}`}
              aria-hidden="true"
            >
              ▸
            </span>
          ) : (
            <span className="content-category-toggle content-category-toggle--empty" aria-hidden="true" />
          )}
          <span className="content-category-icon" aria-hidden="true"><ContentIcon name={category.icon} /></span>
          <span>
            <strong>{title}</strong>
            <small>{isShortcut ? `→ ${category.capability_key}` : `/${category.slug}`}</small>
          </span>
        </button>
        <div className="content-category-row__meta">
          <div className="content-category-row__statuses">
            {isShortcut ? (
              <span
                className={`content-category-status content-category-status--${isDegraded ? "hidden" : "published"}`}
              >
                {isDegraded ? "Возможность недоступна" : "Ссылка на возможность"}
              </span>
            ) : (
              <>
                <span
                  className={`content-category-status content-category-status--${category.is_active ? "visible" : "hidden"}`}
                >
                  {category.is_active ? "Видна" : "Скрыта"}
                </span>
                <span
                  className={`content-category-status content-category-status--${category.published_version_id ? "published" : "draft"}`}
                >
                  {category.published_version_id ? "Опубликована" : "Черновик"}
                </span>
              </>
            )}
          </div>
          {!isShortcut ? (
            <div className="content-category-row__add-actions">
              <button type="button" className="content-add-child" onClick={() => onAddChild(category.id)}>
                + Вложенная
              </button>
              <button type="button" className="content-add-child" onClick={() => onAddShortcut(category.id)}>
                + Ссылка на возможность
              </button>
            </div>
          ) : null}
        </div>
        <div className="content-category-row__order">
          <button type="button" disabled={reordering || first} onClick={() => onMove(category.id, -1)} aria-label="Поднять категорию">↑</button>
          <button type="button" disabled={reordering || last} onClick={() => onMove(category.id, 1)} aria-label="Опустить категорию">↓</button>
        </div>
      </article>
      {isExpanded ? (
        <div className="content-category-children">
          {children.map((child, index) => (
            <CategoryRow
              category={child}
              categories={categories}
              activeId={activeId}
              reordering={reordering}
              onSelect={onSelect}
              onMove={onMove}
              onAddChild={onAddChild}
              onAddShortcut={onAddShortcut}
              enabledCapabilityKeys={enabledCapabilityKeys}
              expandedIds={expandedIds}
              onToggleExpand={onToggleExpand}
              depth={depth + 1}
              first={index === 0}
              last={index === children.length - 1}
              key={child.id}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
