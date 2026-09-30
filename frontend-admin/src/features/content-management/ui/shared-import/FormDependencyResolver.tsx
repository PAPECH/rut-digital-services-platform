import type {
  ContentFormDependency,
  SharedContentDependencyReport,
} from "@/entities/content/model/types";

export type FormResolutionChoice = "auto" | "copy_shared" | `target:${number}`;
export type FormResolutionChoices = Record<number, FormResolutionChoice>;

const statusLabels: Record<ContentFormDependency["status"], string> = {
  resolved: "Связано",
  copy_available: "Можно скопировать",
  mapping_required: "Нужно сопоставить",
  unavailable: "Недоступно",
};

export function FormDependencyResolver({
  report,
  choices,
  onChange,
}: {
  report: SharedContentDependencyReport;
  choices: FormResolutionChoices;
  onChange: (sourceId: number, choice: FormResolutionChoice) => void;
}) {
  if (!report.dependencies.length) {
    return (
      <div className="dependency-wizard-empty">
        <strong>Связанных форм нет</strong>
        <span>Категорию можно импортировать без дополнительных действий.</span>
      </div>
    );
  }

  return (
    <div className="dependency-resolution-list">
      {report.dependencies.map((dependency) => {
        const choice = choices[dependency.source_id] ?? "auto";
        const canSelect = dependency.status !== "unavailable";
        return (
          <article className="dependency-resolution-card" key={dependency.source_id}>
            <div className="dependency-resolution-head">
              <div>
                <strong>{dependency.label}</strong>
                <small>
                  {dependency.source_slug ? `/${dependency.source_slug}` : `#${dependency.source_id}`}
                </small>
              </div>
              <span className={`status-pill dependency-status-${dependency.status}`}>
                {statusLabels[dependency.status]}
              </span>
            </div>

            {dependency.status === "resolved" ? (
              <p className={dependency.matched_target_ready ? "dependency-note" : "dependency-warning"}>
                {dependency.matched_target_ready
                  ? "Автоматически сопоставлено по slug."
                  : "Форма найдена по slug, но её нужно опубликовать и активировать до публикации категории."}
              </p>
            ) : null}
            {dependency.status === "unavailable" ? (
              <p className="dependency-warning">
                Исходная форма удалена или больше не принадлежит боту-источнику.
              </p>
            ) : null}

            {canSelect ? (
              <label>
                <span className="field-label">Как разрешить зависимость</span>
                <select
                  className="input"
                  value={choice}
                  onChange={(event) =>
                    onChange(
                      dependency.source_id,
                      event.target.value as FormResolutionChoice,
                    )
                  }
                >
                  <option value="auto" disabled={dependency.status !== "resolved"}>
                    {dependency.status === "resolved"
                      ? "Использовать совпадение по slug"
                      : "Выберите действие"}
                  </option>
                  {dependency.status === "copy_available" && dependency.can_copy ? (
                    <option value="copy_shared">Скопировать общий черновик формы</option>
                  ) : null}
                  {report.targets.map((target) => (
                    <option value={`target:${target.id}`} key={target.id}>
                      {target.label} · /{target.slug}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}

            {dependency.status === "copy_available" && !dependency.can_copy ? (
              <p className="dependency-note">
                Копирование недоступно без права «Управление формами». Можно выбрать опубликованную форму.
              </p>
            ) : null}
            {dependency.status !== "resolved" &&
            !dependency.can_copy &&
            !report.targets.length ? (
              <p className="dependency-warning">
                В текущем боте нет опубликованных форм для сопоставления.
              </p>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
