export interface DependencyWizardStep {
  id: string;
  label: string;
}

export function DependencyWizardSteps({
  steps,
  activeId,
}: {
  steps: DependencyWizardStep[];
  activeId: string;
}) {
  const activeIndex = steps.findIndex((step) => step.id === activeId);
  return (
    <ol className="dependency-wizard-steps" aria-label="Этапы импорта">
      {steps.map((step, index) => (
        <li
          className={index === activeIndex ? "active" : index < activeIndex ? "done" : ""}
          key={step.id}
          aria-current={index === activeIndex ? "step" : undefined}
        >
          <span>{index + 1}</span>
          {step.label}
        </li>
      ))}
    </ol>
  );
}
