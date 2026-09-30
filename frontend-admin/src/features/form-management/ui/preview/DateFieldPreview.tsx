import type { DateField } from "@/entities/form/model/types";
import { PreviewLabel, type FieldPreviewProps } from "./previewTypes";
export function DateFieldPreview({ field }: FieldPreviewProps<DateField>) {
  return (
    <div>
      <PreviewLabel field={field} />
      <input
        className="input"
        type="date"
        disabled
        value={field.default ?? ""}
        readOnly
      />
    </div>
  );
}
