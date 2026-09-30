import type { NavigationItem } from "@/widgets/admin-shell/model/navigation";
import { AdminNavigationLink } from "@/widgets/admin-shell/ui/AdminNavigationLink";

export function AdminNavigation({
  items,
  onNavigate,
}: {
  items: NavigationItem[];
  onNavigate?: () => void;
}) {
  return (
    <div className="navlinks">
      {items.map((item) => (
        <AdminNavigationLink
          key={item.to}
          item={item}
          onNavigate={onNavigate}
        />
      ))}
    </div>
  );
}
