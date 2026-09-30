import type { FormDraft } from "@/entities/form/model/types";

export function FormMetadataEditor({
  draft,
  onChange,
}: {
  draft: FormDraft;
  onChange: (draft: FormDraft) => void;
}) {
  return (
    <section className="form-builder-meta">
      <label className="content-editor-field">
        <span>Название формы</span>
        <input
          className="input"
          value={draft.name}
          onChange={(event) => onChange({ ...draft, name: event.target.value })}
        />
      </label>
      <label className="content-editor-field">
        <span>Описание</span>
        <textarea
          className="textarea"
          rows={3}
          value={draft.description ?? ""}
          onChange={(event) =>
            onChange({ ...draft, description: event.target.value || null })
          }
        />
      </label>
      <label className="content-editor-field form-builder-meta__wide">
        <span>Ответ после принятия заявки</span>
        <textarea
          className="textarea"
          rows={4}
          value={draft.reply_on_accept ?? ""}
          onChange={(event) =>
            onChange({ ...draft, reply_on_accept: event.target.value || null })
          }
        />
      </label>
    </section>
  );
}
