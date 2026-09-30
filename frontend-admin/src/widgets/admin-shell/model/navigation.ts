import type { ReactNode } from "react";

export interface NavigationItem {
  to: string;
  label: string;
  icon: ReactNode;
  badge?: number;
}
