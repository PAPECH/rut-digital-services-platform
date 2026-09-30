import { useState } from "react";

import { DemoPanel } from "../DemoPanel/DemoPanel";
import { DemoStage } from "../DemoStage/DemoStage";
import { GuideSection, type GuideSectionLink } from "../GuideSection/GuideSection";
import { GuideStepper, type GuideStep } from "../GuideStepper/GuideStepper";
import * as mock from "../MiniAppMock/MiniAppMock.css";
import { flashOnce, hotspot } from "../motion.css";
import { PhoneMockup } from "../PhoneMockup/PhoneMockup";
import * as styles from "./PublishCycleDemo.css";

export const PUBLISH_CYCLE_SECTION: GuideSectionLink = {
  id: "publish-cycle",
  title: "Сохранить → Опубликовать",
};

const OLD_TEXT = "Приём документов — до 10 августа.";
const NEW_TEXT = "Приём документов — до 15 августа.";

const STEPS: ReadonlyArray<GuideStep> = [
  {
    title: "Измените",
    text: "Вы отредактировали текст (здесь — поменяли дату). Пока это только правка на вашем экране. Нажмите «Сохранить».",
  },
  {
    title: "Сохраните",
    text: "«Сохранить» записал черновик. Пользователи бота его не видят — у них по-прежнему старая версия. Нажмите «Опубликовать».",
  },
  {
    title: "Опубликуйте",
    text: "«Опубликовать» выпустил сохранённый черновик. Теперь изменение видят все пользователи.",
  },
];

const STATUS = [
  { tone: "dirty", text: "Есть несохранённые изменения" },
  { tone: "saved", text: "Сохранено · пользователи видят старую версию" },
  { tone: "published", text: "Опубликовано · пользователи видят новое" },
] as const;

/**
 * Shared by every guide tab: an edit reaches students only after «Сохранить» and then
 * «Опубликовать». Steps advance only on click — a step, «Далее», or the ringed button in the
 * demo. As in the real editor, each button is enabled only when it has something to do.
 */
export function PublishCycleDemo() {
  const [step, setStep] = useState(0);
  const published = step === 2;

  return (
    <GuideSection
      {...PUBLISH_CYCLE_SECTION}
      lead="Главное правило для всех разделов: после любого изменения нажмите «Сохранить», затем «Опубликовать»."
    >
      <GuideStepper steps={STEPS} step={step} onStep={setStep} inline />

      <DemoStage interactive>
        <div className={styles.stage}>
          <DemoPanel kind="admin">
            <div className={styles.editor}>
              <span className={styles.editorLabel}>Текст</span>
              <div className={styles.fakeInput}>{NEW_TEXT}</div>
              <div className={styles.actions}>
                <button
                  type="button"
                  className={`btn btn-secondary btn-sm ${step === 0 ? hotspot : ""}`}
                  disabled={step !== 0}
                  onClick={() => setStep(1)}
                >
                  Сохранить
                </button>
                <button
                  type="button"
                  className={`btn btn-primary btn-sm ${step === 1 ? hotspot : ""}`}
                  disabled={step !== 1}
                  onClick={() => setStep(2)}
                >
                  Опубликовать
                </button>
              </div>
              <span className={`${styles.status} ${styles.statusTone[STATUS[step].tone]}`}>
                {STATUS[step].text}
              </span>
            </div>
          </DemoPanel>

          <span className={styles.arrow} aria-hidden>
            →
          </span>

          <DemoPanel kind="result">
            <PhoneMockup title="Поступление">
              <h2 className={mock.heading[2]}>Поступление</h2>
              <div
                key={published ? "new" : "old"}
                className={`${mock.callout} ${published ? flashOnce : ""}`}
              >
                {published ? NEW_TEXT : OLD_TEXT}
              </div>
            </PhoneMockup>
          </DemoPanel>
        </div>
      </DemoStage>
    </GuideSection>
  );
}
