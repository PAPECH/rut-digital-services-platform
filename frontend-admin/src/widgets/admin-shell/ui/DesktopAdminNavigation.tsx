import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";

import { Icon } from "@/components/Icon";
import type { NavigationItem } from "@/widgets/admin-shell/model/navigation";
import { useNavigationOverflow } from "@/widgets/admin-shell/model/useNavigationOverflow";
import { AdminNavigationLink } from "@/widgets/admin-shell/ui/AdminNavigationLink";

function matchesPath(pathname: string, item: NavigationItem): boolean {
  return pathname === item.to || pathname.startsWith(`${item.to}/`);
}

export function DesktopAdminNavigation({ items }: { items: NavigationItem[] }) {
  const location = useLocation();
  const menuRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const measurementRef = useRef<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(false);
  const visibleItemCount = useNavigationOverflow(
    items.length,
    containerRef,
    measurementRef,
  );
  const visibleItems = items.slice(0, visibleItemCount);
  const overflowItems = items.slice(visibleItemCount);
  const overflowActive = overflowItems.some((item) =>
    matchesPath(location.pathname, item),
  );

  useEffect(() => setOpen(false), [location.pathname]);

  useEffect(() => {
    if (!open) return;
    const closeOnOutsideClick = (event: MouseEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setOpen(false);
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
    <div className="desktop-navigation-menu" ref={containerRef}>
      <div className="navlinks">
        {visibleItems.map((item) => (
          <AdminNavigationLink key={item.to} item={item} />
        ))}
      </div>
      {overflowItems.length ? (
        <div className="nav-more" ref={menuRef}>
          <button
            type="button"
            className={`navlink nav-more__button ${overflowActive ? "active" : ""}`}
            aria-haspopup="menu"
            aria-expanded={open}
            onClick={() => setOpen((current) => !current)}
          >
            <span>Ещё</span>
            <span className="ico nav-more__chevron" aria-hidden="true">
              <Icon.ChevronDown />
            </span>
          </button>
          {open ? (
            <div className="nav-more__menu" role="menu">
              {overflowItems.map((item) => (
                <AdminNavigationLink
                  key={item.to}
                  item={item}
                  onNavigate={() => setOpen(false)}
                />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      <div
        className="nav-overflow-measure"
        ref={measurementRef}
        aria-hidden="true"
      >
        {items.map((item) => (
          <div className="navlink" data-navigation-item key={item.to}>
            <span className="ico">{item.icon}</span>
            <span>{item.label}</span>
            {item.badge ? <span className="badge">{item.badge}</span> : null}
          </div>
        ))}
        <div className="navlink" data-navigation-more>
          <span>Ещё</span>
          <span className="ico nav-more__chevron">
            <Icon.ChevronDown />
          </span>
        </div>
      </div>
    </div>
  );
}
