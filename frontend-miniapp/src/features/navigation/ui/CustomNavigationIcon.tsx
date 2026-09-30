import type { BottomNavigationIcon } from "@/api/types";
import { ContentIcon } from "@/entities/content/ui/ContentIcon";

export function CustomNavigationIcon({ icon }: { icon: BottomNavigationIcon }) {
  return <ContentIcon name={icon} />;
}
