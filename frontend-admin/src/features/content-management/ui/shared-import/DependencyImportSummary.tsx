import type {
  SharedContentDependencyReport,
  SharedContentDraft,
} from "@/entities/content/model/types";
import type { FormResolutionChoices } from "./FormDependencyResolver";

function resolutionLabel(
  sourceId: number,
  report: SharedContentDependencyReport,
  choices: FormResolutionChoices,
): string {
  const dependency = report.dependencies.find((item) => item.source_id === sourceId);
  const choice = choices[sourceId] ?? "auto";
  if (!dependency) return "Неизвестная зависимость";
  if (choice === "copy_shared") return "Создать независимый черновик формы";
  if (choice.startsWith("target:")) {
    const target = report.targets.find((item) => item.id === Number(choice.slice(7)));
    return target ? `Использовать «${target.label}»` : "Использовать выбранную форму";
  }
  return dependency.matched_target_ready
    ? "Использовать совпадение по slug"
    : "Использовать совпадение по slug; форму затем подготовить";
}

export function DependencyImportSummary({
  draft,
  slug,
  report,
  choices,
}: {
  draft: SharedContentDraft;
  slug: string;
  report: SharedContentDependencyReport;
  choices: FormResolutionChoices;
}) {
  const copies = Object.values(choices).filter((choice) => choice === "copy_shared").length;
  return (
    <div className="dependency-import-summary">
      <div>
        <span>Категория</span>
        <strong>{draft.title}</strong>
        <small>/{slug}</small>
      </div>
      {report.dependencies.map((dependency) => (
        <div key={dependency.source_id}>
          <span>Форма · {dependency.label}</span>
          <strong>{resolutionLabel(dependency.source_id, report, choices)}</strong>
        </div>
      ))}
      {copies ? (
        <p className="dependency-warning">
          Скопированные формы останутся черновиками. Перед публикацией категории опубликуйте и активируйте их во вкладке «Формы».
        </p>
      ) : null}
    </div>
  );
}
