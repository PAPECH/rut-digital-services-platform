import type { ComponentType } from "react";

import type { CapabilityEditorProps } from "@/entities/capability/model/types";
import { AdmissionRatingCapabilityEditor } from "./AdmissionRatingCapabilityEditor";
import { RequestStatusCapabilityEditor } from "./RequestStatusCapabilityEditor";
import { RutScheduleCapabilityEditor } from "./RutScheduleCapabilityEditor";

const capabilityEditorRegistry: Record<
  string,
  ComponentType<CapabilityEditorProps>
> = {
  admission_rating: AdmissionRatingCapabilityEditor,
  request_status: RequestStatusCapabilityEditor,
  rut_schedule: RutScheduleCapabilityEditor,
};

export function CapabilityEditorRegistry(props: CapabilityEditorProps) {
  const Editor = capabilityEditorRegistry[props.installation.admin_editor_key];
  if (!Editor) {
    return (
      <div className="content-empty-state">
        Редактор этой возможности отсутствует в текущей версии админки.
      </div>
    );
  }
  return <Editor {...props} />;
}
