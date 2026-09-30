export function SystemCollectionBlockFields({
  title,
  description,
  onTitleChange,
}: {
  title: string | null;
  description: string;
  onTitleChange: (title: string | null) => void;
}) {
  return (
    <div className="content-editor-grid">
      <label className="content-editor-wide">
        <span className="field-label">Заголовок блока</span>
        <input
          className="input"
          maxLength={300}
          value={title ?? ""}
          placeholder="Оставьте пустым, чтобы скрыть заголовок"
          onChange={(event) => onTitleChange(event.target.value || null)}
        />
      </label>
      <p className="muted content-editor-wide">{description}</p>
    </div>
  );
}
