import { NavLink } from "react-router-dom";

import type { NavigationItem } from "@/widgets/admin-shell/model/navigation";

export function AdminNavigationLink({
  item,
  onNavigate,
}: {
  item: NavigationItem;
  onNavigate?: () => void;
}) {
  return (
    <NavLink
      to={item.to}
      onClick={onNavigate}
      className={({ isActive }) => `navlink ${isActive ? "active" : ""}`}
    >
      <span className="ico" aria-hidden="true">
        {item.icon}
      </span>
      <span>{item.label}</span>
      {item.badge ? <span className="badge">{item.badge}</span> : null}
    </NavLink>
  );
}
