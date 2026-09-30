import type { FormDraft } from "@/entities/form/model/types";
import { FormFieldPreviewRegistry } from "./FormFieldPreviewRegistry";
export function FormPreview({ draft }: { draft: FormDraft }) {
  return (
    <div className="content-phone-preview">
      <div className="content-phone-screen">
        <h3>{draft.name || "Без названия"}</h3>
        {draft.description ? <p>{draft.description}</p> : null}
        <div style={{ display: "grid", gap: 14 }}>
          {draft.fields
            .filter((f) => f.active)
            .map((field) => (
              <div key={field.key}>
                <FormFieldPreviewRegistry field={field} />
                {field.help_text ? <small>{field.help_text}</small> : null}
              </div>
            ))}
        </div>
        <button
          type="button"
          className="btn btn-primary"
          disabled
          style={{ marginTop: 18 }}
        >
          Отправить
        </button>
      </div>
    </div>
  );
}
