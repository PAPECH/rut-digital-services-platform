import type { CSSProperties, ReactNode } from "react";
import { NavLink } from "react-router-dom";

import { Icon } from "@/components/Icon";
import { usePlatform } from "@/features/platform-manifest/model/PlatformProvider";
import { CustomNavigationIcon } from "@/features/navigation/ui/CustomNavigationIcon";
import { useI18n } from "@/i18n";

interface NavigationItem {
  to: string;
  label: string;
  icon: ReactNode;
  state?: { analyticsSource: "bottom_nav" };
}

function navigationPath(item: {
  target?: "category" | "submission_history" | "form_catalog";
  category_slug: string | null;
}): string {
  if (item.target === "submission_history") return "/submissions";
  if (item.target === "form_catalog") return "/services";
  return `/content/${encodeURIComponent(item.category_slug ?? "")}`;
}

export function BottomNav() {
  const { t } = useI18n();
  const { manifest } = usePlatform();
  const customItems = manifest?.bot.settings.bottom_navigation.custom_items ?? [];
  // Task 054: some bots have no use for a profile screen at all and turn the tab off —
  // defaults to shown (profile?.enabled ?? true) so a manifest predating this setting
  // behaves exactly as it does today.
  const profileTabEnabled = manifest?.bot.settings.profile?.enabled ?? true;
  const items: NavigationItem[] = [
    { to: "/", label: t("home:main:home"), icon: <Icon.Home /> },
    ...customItems.map((item) => ({
      to: navigationPath(item),
      label: item.label,
      icon: <CustomNavigationIcon icon={item.icon} />,
      state: { analyticsSource: "bottom_nav" as const },
    })),
    ...(profileTabEnabled
      ? [{ to: "/profile", label: t("home:main:profile"), icon: <Icon.Profile /> }]
      : []),
  ];

  return (
    <nav
      className="bottom-nav"
      style={{ "--bottom-nav-items": items.length } as CSSProperties}
    >
      {items.map((item) => (
        <NavLink key={item.to} to={item.to} state={item.state} end={item.to === "/"}>
          <span className="ico">{item.icon}</span>
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
