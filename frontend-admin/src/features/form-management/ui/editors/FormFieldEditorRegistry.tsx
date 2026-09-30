import type {
  FormFieldEditorProps,
} from "@/entities/form/model/types";
import { CheckboxFieldEditor } from "./CheckboxFieldEditor";
import { DateFieldEditor } from "./DateFieldEditor";
import { EmailFieldEditor } from "./EmailFieldEditor";
import { FileFieldEditor } from "./FileFieldEditor";
import { LongTextFieldEditor } from "./LongTextFieldEditor";
import { MultiselectFieldEditor } from "./MultiselectFieldEditor";
import { NumberFieldEditor } from "./NumberFieldEditor";
import { PhoneFieldEditor } from "./PhoneFieldEditor";
import { RadioFieldEditor } from "./RadioFieldEditor";
import { SelectFieldEditor } from "./SelectFieldEditor";
import { ShortTextFieldEditor } from "./ShortTextFieldEditor";

export function FormFieldEditorRegistry({
  field,
  onChange,
}: FormFieldEditorProps) {
  switch (field.type) {
    case "short_text":
      return <ShortTextFieldEditor field={field} onChange={onChange} />;
    case "long_text":
      return <LongTextFieldEditor field={field} onChange={onChange} />;
    case "email":
      return <EmailFieldEditor field={field} onChange={onChange} />;
    case "phone":
      return <PhoneFieldEditor field={field} onChange={onChange} />;
    case "number":
      return <NumberFieldEditor field={field} onChange={onChange} />;
    case "date":
      return <DateFieldEditor field={field} onChange={onChange} />;
    case "checkbox":
      return <CheckboxFieldEditor field={field} onChange={onChange} />;
    case "select":
      return <SelectFieldEditor field={field} onChange={onChange} />;
    case "radio":
      return <RadioFieldEditor field={field} onChange={onChange} />;
    case "multiselect":
      return <MultiselectFieldEditor field={field} onChange={onChange} />;
    case "file":
      return <FileFieldEditor field={field} onChange={onChange} />;
  }
}
