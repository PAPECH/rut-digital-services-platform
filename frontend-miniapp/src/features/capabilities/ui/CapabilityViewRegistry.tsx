import type { ComponentType } from "react";

import type { CapabilityViewProps } from "@/entities/capability/model/types";
import { AdmissionRatingCapabilityView } from "./AdmissionRatingCapabilityView";
import { RequestStatusCapabilityView } from "./RequestStatusCapabilityView";
import { RutScheduleCapabilityView } from "./RutScheduleCapabilityView";

const capabilityViewRegistry: Record<
  string,
  ComponentType<CapabilityViewProps>
> = {
  "admission_rating:lookup": AdmissionRatingCapabilityView,
  "request_status:lookup": RequestStatusCapabilityView,
  "rut_schedule:browse": RutScheduleCapabilityView,
};

export function CapabilityViewRegistry(props: CapabilityViewProps) {
  const View =
    capabilityViewRegistry[`${props.capability.key}:${props.viewKey}`];
  if (!View) {
    return (
      <div className="screen platform-error">
        <h1 className="screen-title">Сервис недоступен</h1>
        <p>Этот экран отсутствует в текущей версии приложения.</p>
      </div>
    );
  }
  return <View {...props} />;
}
