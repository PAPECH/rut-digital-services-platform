import { useEffect, useRef, useState } from "react";

import { Icon } from "@/components/Icon";

export interface EntityDropdownPickerItem {
  id: number;
  title: string;
  subtitle?: string;
  badge?: { text: string; tone: "neutral" | "success" };
}

/** A button above the content that opens a popover list to pick one of many entities (forms,
 * tests, …), replacing a permanent left sidebar so the content below can use the full page width
 * -- same open/close-on-outside-click/Escape pattern as `DesktopAdminNavigation`'s "Ещё" menu. */
export function EntityDropdownPicker({
  items,
  activeId,
  reordering = false,
  emptyLabel,
  placeholder,
  onSelect,
  onMove,
}: {
  items: EntityDropdownPickerItem[];
  activeId: number | null;
  reordering?: boolean;
  emptyLabel: string;
  placeholder: string;
  onSelect: (id: number) => void;
  /** Omit when the list has no meaningful order (e.g. a plain filter picker) -- the ↑/↓ controls
   * are hidden entirely rather than rendered as dead buttons. */
  onMove?: (id: number, direction: -1 | 1) => void;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const active = items.find((item) => item.id === activeId) ?? null;

  useEffect(() => {
    if (!open) return;
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <div className="entity-picker" ref={containerRef}>
      <button
        type="button"
        className="entity-picker__button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="entity-picker__button-label">{active ? active.title : placeholder}</span>
        <span className="ico entity-picker__chevron" aria-hidden="true">
          <Icon.ChevronDown />
        </span>
      </button>
      {open && (
        <div className="entity-picker__menu" role="listbox">
          {items.length === 0 && <div className="entity-picker__empty">{emptyLabel}</div>}
          {items.map((item, index) => (
            <div
              key={item.id}
              className={`entity-picker__row ${item.id === activeId ? "active" : ""}`}
            >
              <button
                type="button"
                className="entity-picker__row-main"
                role="option"
                aria-selected={item.id === activeId}
                onClick={() => {
                  onSelect(item.id);
                  setOpen(false);
                }}
              >
                <strong>{item.title}</strong>
                {item.subtitle && <span>{item.subtitle}</span>}
              </button>
              <div className="entity-picker__row-actions">
                {item.badge && <span className={`tag ${item.badge.tone}`}>{item.badge.text}</span>}
                {onMove && (
                  <>
                    <button
                      type="button"
                      className="form-list-order-button"
                      disabled={reordering || index === 0}
                      onClick={() => onMove(item.id, -1)}
                      aria-label="Поднять"
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      className="form-list-order-button"
                      disabled={reordering || index === items.length - 1}
                      onClick={() => onMove(item.id, 1)}
                      aria-label="Опустить"
                    >
                      ↓
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
