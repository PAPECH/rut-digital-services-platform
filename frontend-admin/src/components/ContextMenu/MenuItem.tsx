import { ReactNode } from "react";

interface MenuItemProps {
  onClick: () => void;
  children: ReactNode;
}

function MenuItem({ onClick, children }: MenuItemProps) {
  return (
    <li
      onClick={onClick}
      style={{ padding: "8px 16px", cursor: "pointer" }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "#f0f0f0")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
    >
      {children}
    </li>
  );
}

export default MenuItem;
