import {
  CONTENT_ICONS,
  type ContentIconName,
} from "@/entities/content/model/contentIcons";
import { ContentIcon } from "@/entities/content/ui/ContentIcon";

export function ContentIconPicker({
  value,
  onChange,
}: {
  value: ContentIconName;
  onChange: (value: ContentIconName) => void;
}) {
  return (
    <div className="content-icon-picker">
      <span className="content-icon-picker__preview" aria-hidden="true">
        <ContentIcon name={value} />
      </span>
      <select
        className="select"
        value={value}
        onChange={(event) => onChange(event.target.value as ContentIconName)}
      >
        {CONTENT_ICONS.map((icon) => (
          <option value={icon.value} key={icon.value}>
            {icon.label}
          </option>
        ))}
      </select>
    </div>
  );
}
