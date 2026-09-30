import type { FieldInputProps } from "@/entities/form/model/types";
import { CheckboxFieldInput } from "./CheckboxFieldInput";
import { DateFieldInput } from "./DateFieldInput";
import { EmailFieldInput } from "./EmailFieldInput";
import { FileFieldInput } from "./FileFieldInput";
import { LongTextFieldInput } from "./LongTextFieldInput";
import { MultiselectFieldInput } from "./MultiselectFieldInput";
import { NumberFieldInput } from "./NumberFieldInput";
import { PhoneFieldInput } from "./PhoneFieldInput";
import { RadioFieldInput } from "./RadioFieldInput";
import { SelectFieldInput } from "./SelectFieldInput";
import { ShortTextFieldInput } from "./ShortTextFieldInput";
export function FormFieldInputRegistry(props: FieldInputProps) {
  const { field } = props;
  switch (field.type) {
    case "short_text":
      return <ShortTextFieldInput {...props} field={field} />;
    case "long_text":
      return <LongTextFieldInput {...props} field={field} />;
    case "email":
      return <EmailFieldInput {...props} field={field} />;
    case "phone":
      return <PhoneFieldInput {...props} field={field} />;
    case "number":
      return <NumberFieldInput {...props} field={field} />;
    case "date":
      return <DateFieldInput {...props} field={field} />;
    case "checkbox":
      return <CheckboxFieldInput {...props} field={field} />;
    case "select":
      return <SelectFieldInput {...props} field={field} />;
    case "radio":
      return <RadioFieldInput {...props} field={field} />;
    case "multiselect":
      return <MultiselectFieldInput {...props} field={field} />;
    case "file":
      return <FileFieldInput {...props} field={field} />;
  }
}
