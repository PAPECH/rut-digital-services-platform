import type { ShortTextField } from "@/entities/form/model/types";
import { PreviewLabel, type FieldPreviewProps } from "./previewTypes";
export function ShortTextFieldPreview({
  field,
}: FieldPreviewProps<ShortTextField>) {
  return (
    <div>
      <PreviewLabel field={field} />
      <input
        className="input"
        disabled
        placeholder={field.placeholder ?? ""}
        value={field.default ?? ""}
        readOnly
      />
    </div>
  );
}
