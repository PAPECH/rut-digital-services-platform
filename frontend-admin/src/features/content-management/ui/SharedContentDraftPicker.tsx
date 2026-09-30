import { useEffect, useMemo, useState } from "react";

import type {
  ContentFormDependencyResolution,
  SharedContentDependencyReport,
  SharedContentDraft,
} from "@/entities/content/model/types";
import { copyDraftSlug } from "@/features/shared-drafts/model/copyDraftSlug";
import { DependencyWizardSteps } from "@/features/shared-drafts/ui/DependencyWizardSteps";
import { contentApi } from "../api/contentApi";
import { DependencyImportSummary } from "./shared-import/DependencyImportSummary";
import {
  FormDependencyResolver,
  type FormResolutionChoice,
  type FormResolutionChoices,
} from "./shared-import/FormDependencyResolver";
import { SharedContentDraftSelection } from "./shared-import/SharedContentDraftSelection";

type WizardStage = "draft" | "dependencies" | "confirm";

const steps = [
  { id: "draft", label: "Черновик" },
  { id: "dependencies", label: "Зависимости" },
  { id: "confirm", label: "Проверка" },
];

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : "Не удалось выполнить импорт";
}

function buildResolutions(choices: FormResolutionChoices): ContentFormDependencyResolution[] {
  const resolutions: ContentFormDependencyResolution[] = [];
  Object.entries(choices).forEach(([sourceId, choice]) => {
    if (choice === "auto") return;
    if (choice === "copy_shared") {
      resolutions.push({
        kind: "form",
        source_id: Number(sourceId),
        action: "copy_shared",
      });
      return;
    }
    resolutions.push({
      kind: "form",
      source_id: Number(sourceId),
      action: "use_existing",
      target_id: Number(choice.slice(7)),
    });
  });
  return resolutions;
}

export function SharedContentDraftPicker({
  existingSlugs,
  onImport,
  onClose,
}: {
  existingSlugs: string[];
  onImport: (
    sourceCategoryId: number,
    slug: string,
    resolutions: ContentFormDependencyResolution[],
  ) => Promise<unknown>;
  onClose: () => void;
}) {
  const [items, setItems] = useState<SharedContentDraft[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [slug, setSlug] = useState("");
  const [stage, setStage] = useState<WizardStage>("draft");
  const [report, setReport] = useState<SharedContentDependencyReport | null>(null);
  const [choices, setChoices] = useState<FormResolutionChoices>({});
  const [loading, setLoading] = useState(true);
  const [loadingDependencies, setLoadingDependencies] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const occupied = useMemo(() => new Set(existingSlugs), [existingSlugs]);
  const selected = items.find((item) => item.source_category_id === selectedId) ?? null;

  useEffect(() => {
    let mounted = true;
    void contentApi
      .listSharedDrafts()
      .then((loaded) => {
        if (!mounted) return;
        setItems(loaded);
        const first = loaded[0] ?? null;
        setSelectedId(first?.source_category_id ?? null);
        setSlug(first ? copyDraftSlug(first.slug, occupied) : "");
      })
      .catch((loadError: unknown) => {
        if (mounted) setError(errorText(loadError));
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [occupied]);

  const selectDraft = (item: SharedContentDraft) => {
    setSelectedId(item.source_category_id);
    setSlug(copyDraftSlug(item.slug, occupied));
    setStage("draft");
    setReport(null);
    setChoices({});
    setError(null);
  };

  const openDependencies = async () => {
    if (!selected) return;
    setLoadingDependencies(true);
    setError(null);
    try {
      const loaded = await contentApi.getSharedDraftDependencies(selected.source_category_id);
      setReport(loaded);
      setChoices(
        Object.fromEntries(
          loaded.dependencies.map((dependency) => [
            dependency.source_id,
            dependency.status === "copy_available" && dependency.can_copy
              ? "copy_shared"
              : "auto",
          ]),
        ),
      );
      setStage("dependencies");
    } catch (loadError) {
      setError(errorText(loadError));
    } finally {
      setLoadingDependencies(false);
    }
  };

  const dependenciesComplete = Boolean(
    report &&
      !report.blockers.length &&
      report.dependencies.every(
        (dependency) =>
          dependency.status === "resolved" ||
          (dependency.status !== "unavailable" &&
            (choices[dependency.source_id] ?? "auto") !== "auto"),
      ),
  );

  const submit = async () => {
    if (!selected || !report || !dependenciesComplete) return;
    setSubmitting(true);
    setError(null);
    try {
      await onImport(selected.source_category_id, slug, buildResolutions(choices));
      onClose();
    } catch (importError) {
      setError(errorText(importError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="shared-draft-backdrop"
      role="presentation"
      onMouseDown={submitting ? undefined : onClose}
    >
      <section
        className="shared-draft-dialog dependency-wizard-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Импорт общего черновика категории"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="card-head">
          <div>
            <h2 className="card-title">Импорт общей категории</h2>
            <p className="card-sub">Мастер проверит связанные сущности до создания копии.</p>
          </div>
          <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
            Закрыть
          </button>
        </div>
        <div className="shared-draft-body">
          <DependencyWizardSteps steps={steps} activeId={stage} />
          {loading ? <p className="muted">Загрузка общих черновиков…</p> : null}
          {!loading && !items.length ? (
            <div className="content-empty-state">
              <strong>Общих черновиков пока нет</strong>
              <span>Сотрудник должен сохранить категорию с отметкой «Общий».</span>
            </div>
          ) : null}

          {!loading && stage === "draft" && items.length ? (
            <SharedContentDraftSelection
              items={items}
              selectedId={selectedId}
              slug={slug}
              onSelect={selectDraft}
              onSlugChange={setSlug}
            />
          ) : null}

          {stage === "dependencies" && report ? (
            <>
              {report.blockers.map((blocker) => (
                <div className="dependency-blocker" key={`${blocker.kind}:${blocker.code}`}>
                  <strong>Импорт пока недоступен</strong>
                  <span>
                    В категории {blocker.count} файл(а). Копирование файлов будет добавлено отдельным резолвером.
                  </span>
                </div>
              ))}
              <FormDependencyResolver
                report={report}
                choices={choices}
                onChange={(sourceId: number, choice: FormResolutionChoice) =>
                  setChoices((current) => ({ ...current, [sourceId]: choice }))
                }
              />
            </>
          ) : null}

          {stage === "confirm" && selected && report ? (
            <DependencyImportSummary
              draft={selected}
              slug={slug}
              report={report}
              choices={choices}
            />
          ) : null}

          {error ? <p className="form-error">{error}</p> : null}
          <div className="content-form-actions dependency-wizard-actions">
            {stage !== "draft" ? (
              <button
                type="button"
                className="btn btn-ghost"
                onClick={() => setStage(stage === "confirm" ? "dependencies" : "draft")}
                disabled={submitting}
              >
                Назад
              </button>
            ) : (
              <button type="button" className="btn btn-ghost" onClick={onClose}>
                Отмена
              </button>
            )}
            {stage === "draft" ? (
              <button
                type="button"
                className="btn btn-primary"
                disabled={!selected || slug.length < 2 || loadingDependencies}
                onClick={() => void openDependencies()}
              >
                {loadingDependencies ? "Проверка…" : "Проверить зависимости"}
              </button>
            ) : stage === "dependencies" ? (
              <button
                type="button"
                className="btn btn-primary"
                disabled={!dependenciesComplete}
                onClick={() => setStage("confirm")}
              >
                К проверке
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-primary"
                disabled={submitting}
                onClick={() => void submit()}
              >
                {submitting ? "Импорт…" : "Импортировать"}
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
