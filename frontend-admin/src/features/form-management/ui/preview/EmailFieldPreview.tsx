import type { EmailField } from "@/entities/form/model/types";
import { PreviewLabel, type FieldPreviewProps } from "./previewTypes";
export function EmailFieldPreview({ field }: FieldPreviewProps<EmailField>) {
  return (
    <div>
      <PreviewLabel field={field} />
      <input
        className="input"
        type="email"
        disabled
        placeholder={field.placeholder ?? ""}
        value={field.default ?? ""}
        readOnly
      />
    </div>
  );
}
