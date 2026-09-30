export type FormFieldType =
  | "short_text"
  | "long_text"
  | "email"
  | "phone"
  | "number"
  | "date"
  | "checkbox"
  | "select"
  | "radio"
  | "multiselect"
  | "file";
export interface FormFieldBase {
  key: string;
  type: FormFieldType;
  label: string;
  help_text: string | null;
  required: boolean;
  active: boolean;
  profile_key: string | null;
}
export interface ShortTextField extends FormFieldBase {
  type: "short_text";
  placeholder: string | null;
  default: string | null;
  min_length: number;
  max_length: number;
  pattern: string | null;
}
export interface LongTextField extends Omit<
  ShortTextField,
  "type" | "pattern"
> {
  type: "long_text";
}
export interface EmailField extends FormFieldBase {
  type: "email";
  placeholder: string | null;
  default: string | null;
}
export interface PhoneField extends Omit<EmailField, "type"> {
  type: "phone";
  pattern: string | null;
}
export interface NumberField extends FormFieldBase {
  type: "number";
  placeholder: string | null;
  default: number | null;
  min: number | null;
  max: number | null;
  step: number;
}
export interface DateField extends FormFieldBase {
  type: "date";
  default: string | null;
  min: string | null;
  max: string | null;
}
export interface CheckboxField extends FormFieldBase {
  type: "checkbox";
  default: boolean;
}
export interface FormOption {
  value: string;
  label: string;
}
export interface SelectField extends FormFieldBase {
  type: "select";
  options: FormOption[];
  default: string | null;
}
export interface RadioField extends Omit<SelectField, "type"> {
  type: "radio";
}
export interface MultiselectField extends FormFieldBase {
  type: "multiselect";
  options: FormOption[];
  default: string[] | null;
  min_selected: number | null;
  max_selected: number | null;
}
export interface FileField extends FormFieldBase {
  type: "file";
  accepted_mime_types: string[];
  max_files: number;
  max_size_bytes: number;
}
export type FormField =
  | ShortTextField
  | LongTextField
  | EmailField
  | PhoneField
  | NumberField
  | DateField
  | CheckboxField
  | SelectField
  | RadioField
  | MultiselectField
  | FileField;
export interface PublishedFormSummary {
  id: number;
  slug: string;
  order: number;
  name: string;
  description: string | null;
  version_id: number;
  version: number;
}
export interface PublishedForm extends PublishedFormSummary {
  reply_on_accept: string | null;
  fields: FormField[];
  published_at: string;
}
export interface FieldInputProps<T extends FormField = FormField> {
  field: T;
  value: unknown;
  onChange: (value: unknown) => void;
  disabled?: boolean;
}
export interface UploadedAttachment {
  id: number;
  url: string;
  name: string;
  mime: string;
  size_bytes: number;
}
