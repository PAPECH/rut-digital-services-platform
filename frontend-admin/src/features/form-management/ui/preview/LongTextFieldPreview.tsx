import type { LongTextField } from "@/entities/form/model/types";
import { PreviewLabel, type FieldPreviewProps } from "./previewTypes";
export function LongTextFieldPreview({
  field,
}: FieldPreviewProps<LongTextField>) {
  return (
    <div>
      <PreviewLabel field={field} />
      <textarea
        className="textarea"
        disabled
        placeholder={field.placeholder ?? ""}
        value={field.default ?? ""}
        readOnly
      />
    </div>
  );
}
