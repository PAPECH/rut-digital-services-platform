import { useState } from "react";

import type { RadioField } from "@/entities/form/model/types";
import { formFieldTypeLabel } from "@/features/form-management/model/fieldTypes";
import { FormFieldPreviewRegistry } from "@/features/form-management/ui/preview/FormFieldPreviewRegistry";

import { DemoPanel } from "../../shared/DemoPanel/DemoPanel";
import { DemoStage } from "../../shared/DemoStage/DemoStage";
import { GuideStepper, type GuideStep } from "../../shared/GuideStepper/GuideStepper";
import { changed, flashOnce } from "../../shared/motion.css";
import { PhoneMockup } from "../../shared/PhoneMockup/PhoneMockup";
import { sampleField } from "../model/fieldGuide";
import * as styles from "./FieldCreationDemo.css";

const RADIO_LABEL = formFieldTypeLabel("radio");

const STEPS: ReadonlyArray<GuideStep> = [
  { title: "Создайте форму", text: "«Новая форма» → введите название → «Создать»." },
  {
    title: "Добавьте поле",
    text: `В меню «Добавить поле…» выберите тип ответа — здесь «${RADIO_LABEL}».`,
  },
  {
    title: "Назовите поле",
    text: "«Название поля» — это вопрос, который увидит пользователь. «Обязательное» — без ответа форму не отправить.",
  },
  {
    title: "Настройте",
    text: "«Настроить» — варианты ответа, «Подсказка пользователю», ограничения. Порядок полей — стрелками ↑ ↓.",
  },
  {
    title: "Сохраните и опубликуйте",
    text: "До публикации пользователи видят прежнюю версию формы.",
  },
];

const OPTIONS = (sampleField("radio") as RadioField).options;

/** Steps, the builder after the selected step, and the form the user will see. */
export function FieldCreationDemo() {
  const [step, setStep] = useState(0);
  const field: RadioField = {
    ...(sampleField("radio") as RadioField),
    required: step >= 2,
    options: step >= 3 ? OPTIONS : [],
  };

  return (
    <div className={styles.layout}>
      <DemoPanel
        kind="steps"
        hint="Нажмите на шаг или «Далее» — в демонстрации ниже конструктор и форма в этом состоянии."
      >
        <GuideStepper steps={STEPS} step={step} onStep={setStep} />
      </DemoPanel>

      <DemoStage>
        <div className={styles.stageGrid}>
          <DemoPanel kind="admin" hint="Жёлтым отмечено то, что изменилось на этом шаге.">
            <div className={styles.builder}>
              <div className={`${styles.fakeControl} ${step === 0 ? changed : ""}`}>
                <strong>Заявка на заселение</strong>
              </div>
              {step >= 1 ? (
                <div className={`${styles.fakeControl} ${step === 1 ? changed : ""}`}>
                  {step === 1 ? `Добавить поле… → ${RADIO_LABEL}` : "Добавить поле…"}
                  <span aria-hidden>▾</span>
                </div>
              ) : null}
              {step >= 2 ? (
                <div className={styles.builderRow}>
                  <span className={styles.fieldLabel}>Название поля · {RADIO_LABEL}</span>
                  <div className={`${styles.fakeControl} ${step === 2 ? changed : ""}`}>
                    {field.label}
                  </div>
                  <span className={styles.toggle}>
                    <span className={`${styles.toggleBox} ${styles.toggleBoxOn}`}>✓</span>
                    Обязательное
                  </span>
                  {step >= 3 ? (
                    <div className={`${styles.options} ${step === 3 ? changed : ""}`}>
                      {OPTIONS.map((option) => (
                        <span key={option.value} className={styles.option}>
                          {option.label}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
              {step >= 4 ? (
                <div className={`${styles.actions} ${changed}`}>
                  <span className="btn btn-secondary btn-sm">Сохранить</span>
                  <span className="btn btn-primary btn-sm">Опубликовать</span>
                </div>
              ) : null}
            </div>
          </DemoPanel>

          <DemoPanel kind="result">
            <PhoneMockup title="Заявка на заселение">
              <p className={styles.formTitle}>Заявка на заселение</p>
              {step >= 2 ? (
                <div
                  key={step === 4 ? "published" : "draft"}
                  className={step === 4 ? flashOnce : ""}
                >
                  <FormFieldPreviewRegistry field={field} />
                </div>
              ) : (
                <span className={styles.empty}>Полей пока нет</span>
              )}
            </PhoneMockup>
          </DemoPanel>
        </div>
      </DemoStage>
    </div>
  );
}
