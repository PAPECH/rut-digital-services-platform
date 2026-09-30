import type { SelectField } from "@/entities/form/model/types";
import { PreviewLabel, type FieldPreviewProps } from "./previewTypes";
export function SelectFieldPreview({ field }: FieldPreviewProps<SelectField>) {
  return (
    <div>
      <PreviewLabel field={field} />
      <select className="select" disabled value={field.default ?? ""}>
        <option value="">Выберите…</option>
        {field.options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
