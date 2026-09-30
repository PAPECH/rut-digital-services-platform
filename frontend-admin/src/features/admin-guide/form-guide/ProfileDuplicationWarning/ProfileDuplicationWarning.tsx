import { useState } from "react";

import { coreProfileFields } from "@/entities/profile/model/profileFields";

import { DemoStage } from "../../shared/DemoStage/DemoStage";
import { GuideStepper } from "../../shared/GuideStepper/GuideStepper";
import * as styles from "./ProfileDuplicationWarning.css";

const STEPS = [
  {
    title: "Было: дубли профиля",
    text: "Форма заново спрашивает ФИО и телефон, которые уже есть в профиле.",
  },
  {
    title: "Стало: только новое",
    text: "ФИО и телефон придут в заявку из профиля — спрашиваем только номер комнаты.",
  },
];

/**
 * «Don't re-ask profile data». The listed fields come from `coreProfileFields`, so the warning
 * follows the profile model instead of a hand-typed copy.
 */
export function ProfileDuplicationWarning() {
  const [step, setStep] = useState(0);
  const fixed = step === 1;
  return (
    <div className={styles.box}>
      <div className={styles.text}>
        <h3 className={styles.title}>Не спрашивайте то, что уже есть в профиле</h3>
        <p className={styles.paragraph}>
          Данные профиля пользователя автоматически прикладываются к каждой заявке — сотрудник видит
          их в карточке заявки. Не создавайте поля для:
        </p>
        <div className={styles.chips}>
          {coreProfileFields.map((field) => (
            <span key={field} className={styles.chip}>
              {field}
            </span>
          ))}
        </div>
        <p className={styles.paragraph}>
          Если значение всё же должно быть в самой форме (например, чтобы пользователь мог указать
          другую почту), заполните в настройках поля «Подставлять из поля профиля» — поле заполнится
          само, пользователю останется только проверить.
        </p>
      </div>

      <div className={styles.demo}>
        <GuideStepper steps={STEPS} step={step} onStep={setStep} inline />
        <DemoStage>
          <div className={styles.fields}>
            <span className={styles.tag}>Поля формы в конструкторе</span>
            {["Ваше ФИО", "Ваш телефон"].map((label) => (
              <div key={label} className={styles.row}>
                <span key={fixed ? "struck" : "plain"} className={fixed ? styles.struck : ""}>
                  {label}
                </span>
                <span className={styles.tag}>
                  {label === "Ваш телефон" ? "Телефон" : "Короткий текст"}
                </span>
              </div>
            ))}
            {fixed ? (
              <div className={styles.replacement}>
                <strong>✓ ФИО и телефон придут из профиля</strong>
              </div>
            ) : null}
            <div className={styles.row}>
              <span>Номер комнаты</span>
              <span className={styles.tag}>Короткий текст</span>
            </div>
          </div>
        </DemoStage>
      </div>
    </div>
  );
}
