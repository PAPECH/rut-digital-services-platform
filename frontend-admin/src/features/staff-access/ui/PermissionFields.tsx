import {
  PERMISSION_LABELS,
  type StaffPermissions,
} from "@/features/staff-access/model/types";

export function PermissionFields({
  value,
  disabled = false,
  onChange,
}: {
  value: StaffPermissions;
  disabled?: boolean;
  onChange: (next: StaffPermissions) => void;
}) {
  return (
    <div className="staff-permissions">
      {PERMISSION_LABELS.map(({ key, label }) => (
        <label key={key} className="staff-permission">
          <input
            type="checkbox"
            checked={value[key]}
            disabled={disabled}
            onChange={(event) =>
              onChange({ ...value, [key]: event.target.checked })
            }
          />
          <span>{label}</span>
        </label>
      ))}
    </div>
  );
}

