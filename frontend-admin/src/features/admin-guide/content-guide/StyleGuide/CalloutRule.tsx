import { DoDontPair } from "../../shared/DoDontPair/DoDontPair";
import * as mock from "../../shared/MiniAppMock/MiniAppMock.css";
import { PhoneMockup } from "../../shared/PhoneMockup/PhoneMockup";
import * as styles from "./StyleGuide.css";

/** «Плашка» is for what must not be missed; one or two per page. */
export function CalloutRule() {
  return (
    <div className={styles.rule}>
      <h3 className={styles.ruleTitle}>Плашка — только для важного</h3>
      <p className={styles.ruleText}>
        Стиль плашки несёт смысл: «Информация» (синий) — справка, «Предупреждение» (жёлтый) — сроки
        и условия, «Успех» (зелёный) — «открыто / получилось», «Ошибка» (красный) — запрет или риск.
        Одна-две плашки на страницу.
      </p>
      <DoDontPair
        good={{
          example: (
            <PhoneMockup title="Оплата проживания">
              <h2 className={mock.heading[2]}>Оплата проживания</h2>
              <p className={mock.paragraph}>Оплатить можно в личном кабинете или в банке.</p>
              <div className={`${mock.callout} ${mock.calloutTone.warning}`}>
                <b className={mock.calloutTitle}>Срок оплаты</b>до 10 числа каждого месяца.
              </div>
              <p className={mock.paragraph}>Квитанция приходит на почту.</p>
            </PhoneMockup>
          ),
          caption: "Выделен один ключевой факт — срок. Его невозможно пропустить.",
        }}
        bad={{
          example: (
            <PhoneMockup title="Оплата проживания">
              <h2 className={mock.heading[2]}>Оплата проживания</h2>
              <div className={`${mock.callout} ${mock.calloutTone.info}`}>
                Оплатить можно в личном кабинете или в банке.
              </div>
              <div className={`${mock.callout} ${mock.calloutTone.danger}`}>
                Срок оплаты — до 10 числа.
              </div>
              <div className={`${mock.callout} ${mock.calloutTone.success}`}>
                Квитанция приходит на почту.
              </div>
            </PhoneMockup>
          ),
          caption: "Плашкой оформлен каждый абзац, цвета случайные — глаз не знает, куда смотреть.",
        }}
      />
    </div>
  );
}
