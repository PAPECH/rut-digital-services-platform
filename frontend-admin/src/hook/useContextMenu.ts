import { useState, useEffect, useRef, MouseEvent, RefObject } from "react";
import { ContextMenuState } from "@/api/types";

interface UseContextMenuReturn {
  contextMenu: ContextMenuState | null;
  menuRef: RefObject<HTMLUListElement>;
  openMenu: (
    e: MouseEvent,
    itemId: number,
    isFavorite: boolean,
    isOpen: boolean,
  ) => void;
  closeMenu: () => void;
}

export function useContextMenu(): UseContextMenuReturn {
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const menuRef = useRef<HTMLUListElement>(null);

  const openMenu = (
    e: MouseEvent,
    itemId: number,
    isFavorite: boolean,
    isOpen: boolean,
  ): void => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({ x: e.clientX, y: e.clientY, itemId, isFavorite, isOpen });
  };

  const closeMenu = (): void => setContextMenu(null);

  useEffect(() => {
    if (!contextMenu) return;

    const handleClickOutside = (e: globalThis.MouseEvent): void => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        closeMenu();
      }
    };

    const handleEscape = (e: KeyboardEvent): void => {
      if (e.key === "Escape") closeMenu();
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [contextMenu]);

  return { contextMenu, menuRef, openMenu, closeMenu };
}
