import { useState } from "react";

import type {
  ContentBlockType,
  NestedContentBlockType,
} from "@/entities/content/model/types";
import { blockLabels } from "@/features/content-management/lib/blockFactory";

const nestedTypes: NestedContentBlockType[] = [
  "heading",
  "paragraph",
  "callout",
  "contact_list",
  "accordion",
  "steps",
  "link",
  "file_list",
  "form_action",
  "test_action",
  "capability_action",
];
const rootOnlyTypes: ContentBlockType[] = [
  "form_catalog",
  "submission_history",
  "test_catalog",
  "test_attempt_history",
  "faq_list",
  "news_list",
  "category_grid",
];

export function BlockTypePicker({
  allowTabs,
  excludeTypes = [],
  onAdd,
}: {
  allowTabs: boolean;
  excludeTypes?: ContentBlockType[];
  onAdd: (type: ContentBlockType) => void;
}) {
  const availableTypes: ContentBlockType[] = allowTabs
    ? [...nestedTypes, ...rootOnlyTypes, "tabs"]
    : nestedTypes;
  const types = availableTypes.filter((type) => !excludeTypes.includes(type));
  const [selected, setSelected] = useState<ContentBlockType>("paragraph");
  const activeType = types.includes(selected) ? selected : types[0];

  return (
    <div className="content-block-picker">
      <select
        className="select"
        aria-label="Тип нового блока"
        value={activeType}
        onChange={(event) =>
          setSelected(event.target.value as ContentBlockType)
        }
      >
        {types.map((type) => (
          <option key={type} value={type}>
            {blockLabels[type]}
          </option>
        ))}
      </select>
      <button
        type="button"
        className="btn btn-secondary"
        disabled={!types.length}
        onClick={() => {
          if (activeType) onAdd(activeType);
        }}
      >
        Добавить блок
      </button>
    </div>
  );
}
