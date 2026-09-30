import type { ReactNode } from "react";

import * as styles from "./GuideStepper.css";

export interface GuideStep {
  title: string;
  text?: ReactNode;
}

/**
 * Manual step-through for guide demos: any step can be clicked and stays selected; «Назад» /
 * «Далее» walk in order. Nothing advances on its own.
 */
export function GuideStepper({
  steps,
  step,
  onStep,
  inline = false,
}: {
  steps: ReadonlyArray<GuideStep>;
  step: number;
  onStep: (step: number) => void;
  /** Compact pill row instead of a vertical list (for short, title-only steps). */
  inline?: boolean;
}) {
  const last = steps.length - 1;
  return (
    <div className={styles.root}>
      <ol className={inline ? styles.listInline : styles.list}>
        {steps.map((item, index) => {
          const state = index === step ? styles.itemActive : index < step ? styles.itemDone : "";
          return (
            <li key={item.title}>
              <button
                type="button"
                className={[styles.item, inline ? styles.itemInline : "", state].join(" ")}
                aria-current={index === step ? "step" : undefined}
                onClick={() => onStep(index)}
              >
                <span className={styles.number}>{index < step ? "✓" : index + 1}</span>
                <span>
                  {inline ? item.title : <span className={styles.itemTitle}>{item.title}</span>}
                  {!inline && item.text ? item.text : null}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
      {inline && steps[step]?.text ? <p className={styles.current}>{steps[step].text}</p> : null}
      <div className={styles.controls}>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={step === 0}
          onClick={() => onStep(step - 1)}
        >
          ← Назад
        </button>
        {step < last ? (
          <button type="button" className="btn btn-primary btn-sm" onClick={() => onStep(step + 1)}>
            Далее →
          </button>
        ) : (
          <button type="button" className="btn btn-secondary btn-sm" onClick={() => onStep(0)}>
            ↺ Сначала
          </button>
        )}
        <span className={styles.counter}>
          Шаг {step + 1} из {steps.length}
        </span>
      </div>
    </div>
  );
}
