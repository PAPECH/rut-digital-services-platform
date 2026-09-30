import { useState } from "react";

import { blockLabels } from "@/features/content-management/lib/blockFactory";

import { DemoPanel } from "../../shared/DemoPanel/DemoPanel";
import { GuideStepper, type GuideStep } from "../../shared/GuideStepper/GuideStepper";
import * as mock from "../../shared/MiniAppMock/MiniAppMock.css";
import { DemoStage } from "../../shared/DemoStage/DemoStage";
import { changed } from "../../shared/motion.css";
import { PhoneMockup } from "../../shared/PhoneMockup/PhoneMockup";
import { FormActionExample, SubmissionHistoryExample } from "../block-examples/FormBlockExamples";
import * as styles from "./FormEmbedGuide.css";

const STEPS: ReadonlyArray<GuideStep> = [
  {
    title: "Создайте и опубликуйте форму",
    text: "В разделе «Конструктор форм»: поля, затем «Сохранить» → «Опубликовать». Пока форма не опубликована, пользователь не сможет её открыть.",
  },
  {
    title: `Добавьте «${blockLabels.form_action}» или «${blockLabels.form_catalog}»`,
    text: `Одна форма по теме страницы — «${blockLabels.form_action}», выберите форму из списка. Все формы бота на одной странице — «${blockLabels.form_catalog}» (в него попадают формы с галочкой «В общем каталоге»).`,
  },
  {
    title: `Ниже добавьте «${blockLabels.submission_history}»`,
    text: "Пользователь увидит отправленные заявки и их статусы и не будет спрашивать «а что с моей заявкой?».",
  },
  {
    title: "Сохраните и опубликуйте страницу",
    text: "Блоки появятся у пользователей только после «Сохранить» → «Опубликовать» в редакторе категории.",
  },
];

/** Steps on the left; the page on the right shows the state after the selected step. */
export function FormEmbedGuide() {
  const [step, setStep] = useState(0);
  return (
    <div className={styles.layout}>
      <DemoPanel
        kind="steps"
        hint="Нажмите на шаг или «Далее» — в демонстрации справа страница в этом состоянии."
      >
        <GuideStepper steps={STEPS} step={step} onStep={setStep} />
      </DemoPanel>
      <DemoStage>
        <DemoPanel kind="result" hint="Жёлтым отмечено то, что появилось на этом шаге.">
          <PhoneMockup title="Заявки и обращения">
            <h2 className={mock.heading[2]}>Заявки и обращения</h2>
            <p className={mock.paragraph}>Выберите, с чем нужна помощь.</p>
            {step === 0 ? (
              <span className={styles.placeholder}>Здесь появится карточка формы</span>
            ) : null}
            {step >= 1 ? (
              <div key="form" className={`${styles.blockEnter} ${step === 1 ? changed : ""}`}>
                <FormActionExample />
              </div>
            ) : null}
            {step >= 2 ? (
              <div key="history" className={`${styles.blockEnter} ${step === 2 ? changed : ""}`}>
                <SubmissionHistoryExample />
              </div>
            ) : null}
          </PhoneMockup>
        </DemoPanel>
      </DemoStage>
    </div>
  );
}
