import { LargeTile } from "@/components/Tiles";
import { Icon } from "@/components/Icon";
import { usePlatform } from "@/features/platform-manifest/model/PlatformProvider";

export function CapabilityGrid() {
  const { manifest } = usePlatform();
  const views =
    manifest?.capabilities.flatMap((capability) =>
      capability.views.map((view) => ({ capability, view })),
    ) || [];
  if (!views.length) return null;
  return (
    <div className="tile-grid">
      {views.map(({ capability, view }) => (
        <LargeTile
          key={`${capability.key}:${view.key}`}
          color="light"
          to={view.path}
          icon={<Icon.Search />}
          title={view.title}
          sub={view.subtitle || ""}
        />
      ))}
    </div>
  );
}
