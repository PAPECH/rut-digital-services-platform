import type { ProfileFieldDefinition } from "@/api/types";
import { ProfileFieldInput } from "@/features/profile-editing/ui/ProfileFieldInput";

export function CustomProfileFields({
  fields,
  values,
  onChange,
}: {
  fields: ProfileFieldDefinition[];
  values: Record<string, unknown>;
  onChange: (key: string, value: unknown) => void;
}) {
  if (!fields.length) return null;
  return (
    <div className="profile-custom-fields">
      {fields.map((field) => (
        <ProfileFieldInput
          key={field.key}
          field={field}
          value={values[field.key]}
          onChange={(value) => onChange(field.key, value)}
        />
      ))}
    </div>
  );
}
