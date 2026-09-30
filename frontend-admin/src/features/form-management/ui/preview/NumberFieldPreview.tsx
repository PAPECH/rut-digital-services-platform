import type { NumberField } from "@/entities/form/model/types";
import { PreviewLabel, type FieldPreviewProps } from "./previewTypes";
export function NumberFieldPreview({ field }: FieldPreviewProps<NumberField>) {
  return (
    <div>
      <PreviewLabel field={field} />
      <input
        className="input"
        type="number"
        disabled
        placeholder={field.placeholder ?? ""}
        value={field.default ?? ""}
        readOnly
      />
    </div>
  );
}
