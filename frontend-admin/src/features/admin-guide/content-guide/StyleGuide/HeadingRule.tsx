import { DoDontPair } from "../../shared/DoDontPair/DoDontPair";
import * as mock from "../../shared/MiniAppMock/MiniAppMock.css";
import * as styles from "./StyleGuide.css";
import { TapToPageMock } from "./TapToPageMock";

/** Page title is an H2 that repeats the tapped card's text; deeper levels go H3 → H4. */
export function HeadingRule() {
  return (
    <div className={styles.rule}>
      <h3 className={styles.ruleTitle}>Заголовок страницы — H2, как на карточке</h3>
      <p className={styles.ruleText}>
        Первый блок каждой страницы (кроме главной) — «Заголовок» уровня H2. Его текст совпадает с
        подписью карточки или вкладки, с которой пользователь пришёл: так он понимает, что попал
        куда хотел. Мини-приложение само название категории не выводит. Разделы страницы — H3,
        подразделы — H4; уровни не пропускайте.
      </p>
      <DoDontPair
        good={{
          example: (
            <TapToPageMock
              tileTitle="Заселение"
              page={
                <>
                  <h2 className={mock.heading[2]}>Заселение</h2>
                  <p className={mock.paragraph}>Порядок заселения для первокурсников.</p>
                  <h3 className={mock.heading[3]}>Какие документы нужны</h3>
                </>
              }
            />
          ),
          caption: "Нажали «Заселение» — видим H2 «Заселение», разделы — H3.",
        }}
        bad={{
          example: (
            <TapToPageMock
              tileTitle="Заселение"
              page={
                <>
                  <h2 className={`${mock.heading[2]} ${styles.bad}`}>
                    Порядок и правила заселения в общежития
                  </h2>
                  <p className={mock.paragraph}>Порядок заселения для первокурсников.</p>
                </>
              }
            />
          ),
          caption:
            "Заголовок не похож на карточку — пользователь сомневается, туда ли попал. Страница без заголовка — так же плохо.",
        }}
      />
    </div>
  );
}
