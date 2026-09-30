import type { FieldPreviewProps } from "./previewTypes";
import { CheckboxFieldPreview } from "./CheckboxFieldPreview";
import { DateFieldPreview } from "./DateFieldPreview";
import { EmailFieldPreview } from "./EmailFieldPreview";
import { FileFieldPreview } from "./FileFieldPreview";
import { LongTextFieldPreview } from "./LongTextFieldPreview";
import { MultiselectFieldPreview } from "./MultiselectFieldPreview";
import { NumberFieldPreview } from "./NumberFieldPreview";
import { PhoneFieldPreview } from "./PhoneFieldPreview";
import { RadioFieldPreview } from "./RadioFieldPreview";
import { SelectFieldPreview } from "./SelectFieldPreview";
import { ShortTextFieldPreview } from "./ShortTextFieldPreview";
export function FormFieldPreviewRegistry({ field }: FieldPreviewProps) {
  switch (field.type) {
    case "short_text":
      return <ShortTextFieldPreview field={field} />;
    case "long_text":
      return <LongTextFieldPreview field={field} />;
    case "email":
      return <EmailFieldPreview field={field} />;
    case "phone":
      return <PhoneFieldPreview field={field} />;
    case "number":
      return <NumberFieldPreview field={field} />;
    case "date":
      return <DateFieldPreview field={field} />;
    case "checkbox":
      return <CheckboxFieldPreview field={field} />;
    case "select":
      return <SelectFieldPreview field={field} />;
    case "radio":
      return <RadioFieldPreview field={field} />;
    case "multiselect":
      return <MultiselectFieldPreview field={field} />;
    case "file":
      return <FileFieldPreview field={field} />;
  }
}
