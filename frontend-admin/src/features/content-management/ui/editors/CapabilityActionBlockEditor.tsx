import { useEffect, useMemo, useState } from "react";

import { api } from "@/api/client";
import type {
  BlockEditorProps,
  CapabilityActionBlock,
} from "@/entities/content/model/types";
import { EditorField } from "./EditorFields";

interface PublicCapability {
  key: string;
  views: Array<{ key: string; title: string }>;
}

interface Manifest {
  capabilities: PublicCapability[];
}

export function CapabilityActionBlockEditor({
  block,
  onChange,
}: BlockEditorProps<CapabilityActionBlock>) {
  const [capabilities, setCapabilities] = useState<PublicCapability[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  useEffect(() => {
    let active = true;
    api
      .get<Manifest>("/manifest")
      .then((result) => {
        if (active) setCapabilities(result.capabilities || []);
      })
      .catch(() => {
        if (active) setLoadError("Не удалось загрузить включённые возможности");
      });
    return () => {
      active = false;
    };
  }, []);
  const views = useMemo(
    () =>
      capabilities.find((item) => item.key === block.capability_key)?.views ||
      [],
    [block.capability_key, capabilities],
  );
  const selectCapability = (capabilityKey: string) => {
    const firstView = capabilities.find((item) => item.key === capabilityKey)
      ?.views[0];
    onChange({
      ...block,
      capability_key: capabilityKey,
      view_key: firstView?.key || "",
      title: firstView?.title || block.title,
    });
  };

  return (
    <div className="content-editor-grid">
      <EditorField label="Возможность">
        <select
          className="select"
          value={block.capability_key}
          onChange={(event) => selectCapability(event.target.value)}
        >
          {!capabilities.some((item) => item.key === block.capability_key) ? (
            <option value={block.capability_key}>{block.capability_key}</option>
          ) : null}
          {capabilities.map((capability) => (
            <option key={capability.key} value={capability.key}>
              {capability.key}
            </option>
          ))}
        </select>
      </EditorField>
      <EditorField label="Экран">
        <select
          className="select"
          value={block.view_key}
          onChange={(event) =>
            onChange({ ...block, view_key: event.target.value })
          }
        >
          {!views.some((view) => view.key === block.view_key) ? (
            <option value={block.view_key}>{block.view_key}</option>
          ) : null}
          {views.map((view) => (
            <option key={view.key} value={view.key}>
              {view.title}
            </option>
          ))}
        </select>
      </EditorField>
      <EditorField label="Текст кнопки">
        <input
          className="input"
          value={block.title}
          onChange={(event) =>
            onChange({ ...block, title: event.target.value })
          }
        />
      </EditorField>
      <div className="content-editor-wide">
        <EditorField label="Описание">
          <textarea
            className="textarea"
            rows={2}
            value={block.description ?? ""}
            onChange={(event) =>
              onChange({ ...block, description: event.target.value || null })
            }
          />
        </EditorField>
      </div>
      {loadError ? (
        <p className="form-error content-editor-wide">{loadError}</p>
      ) : null}
    </div>
  );
}
