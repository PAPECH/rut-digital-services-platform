import type { PhoneField } from "@/entities/form/model/types";
import { PreviewLabel, type FieldPreviewProps } from "./previewTypes";
export function PhoneFieldPreview({ field }: FieldPreviewProps<PhoneField>) {
  return (
    <div>
      <PreviewLabel field={field} />
      <input
        className="input"
        type="tel"
        disabled
        placeholder={field.placeholder ?? ""}
        value={field.default ?? ""}
        readOnly
      />
    </div>
  );
}
