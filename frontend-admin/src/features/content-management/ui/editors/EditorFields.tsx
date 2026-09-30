import { useId, type ReactNode } from "react";

export function EditorField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="content-editor-field">
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}

/**
 * Labelled wrapper for a field whose control contains buttons (rich-text toolbar, file
 * pickers). A `<label>` there would forward every click inside it to its first button — e.g. the
 * rich-text «Ж», bolding whatever was just selected — so this uses a named group instead.
 */
export function EditorFieldGroup({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const labelId = useId();
  return (
    <div className="content-editor-field" role="group" aria-labelledby={labelId}>
      <span id={labelId} className="field-label">{label}</span>
      {children}
    </div>
  );
}

export function ItemActions({
  onAdd,
  onRemove,
  addLabel = "Добавить",
}: {
  onAdd?: () => void;
  onRemove?: () => void;
  addLabel?: string;
}) {
  return (
    <div className="content-item-actions">
      {onRemove ? (
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={onRemove}
        >
          Удалить
        </button>
      ) : null}
      {onAdd ? (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={onAdd}
        >
          {addLabel}
        </button>
      ) : null}
    </div>
  );
}
