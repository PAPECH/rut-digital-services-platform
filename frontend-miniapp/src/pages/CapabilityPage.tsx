import { useEffect } from "react";
import { useParams } from "react-router-dom";

import { capabilityApi } from "@/features/capabilities/api/capabilityApi";
import { CapabilityViewRegistry } from "@/features/capabilities/ui/CapabilityViewRegistry";
import { usePlatform } from "@/features/platform-manifest/model/PlatformProvider";

export function CapabilityPage() {
  const { capabilityKey, viewKey } = useParams();
  const { manifest } = usePlatform();
  const capability = manifest?.capabilities.find(
    (item) => item.key === capabilityKey,
  );
  const view = capability?.views.find((item) => item.key === viewKey);
  useEffect(() => {
    if (capability && view) {
      void capabilityApi
        .viewOpened(capability.key, capability.installation_id, view.key)
        .catch(() => undefined);
    }
  }, [capability, view]);
  if (!capability || !view || !viewKey) {
    return (
      <div className="screen platform-error">
        <h1 className="screen-title">Сервис недоступен</h1>
        <p>Возможность отключена или не настроена для этого бота.</p>
      </div>
    );
  }
  return (
    <main className="screen">
      <CapabilityViewRegistry capability={capability} viewKey={viewKey} />
    </main>
  );
}
