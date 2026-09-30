import type { ProfileFieldDefinition } from "@/api/types";

export function ProfileFieldInput({
  field,
  value,
  onChange,
}: {
  field: ProfileFieldDefinition;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  if (field.type === "boolean") {
    return (
      <label className="profile-boolean-field">
        <input type="checkbox" checked={value === true} onChange={(event) => onChange(event.target.checked)} />
        <span>{field.label}{field.required ? " *" : ""}</span>
      </label>
    );
  }

  const label = <label className="field-label profile-field-gap">{field.label}{field.required ? " *" : ""}</label>;
  if (field.type === "select") {
    return (
      <>
        {label}
        <select className="select" value={String(value ?? "")} onChange={(event) => onChange(event.target.value)}>
          <option value="">Выберите…</option>
          {(field.options ?? []).map((option) => <option value={option} key={option}>{option}</option>)}
        </select>
      </>
    );
  }

  return (
    <>
      {label}
      <input
        className="input"
        type={field.type === "string" || field.type === "phone" ? "text" : field.type}
        value={String(value ?? "")}
        onChange={(event) => onChange(event.target.value)}
      />
    </>
  );
}
