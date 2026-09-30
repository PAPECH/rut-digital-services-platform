import * as mock from "../../shared/MiniAppMock/MiniAppMock.css";

const LEVELS = [
  { level: 1, text: "H1 — заголовок экрана" },
  { level: 2, text: "H2 — название страницы" },
  { level: 3, text: "H3 — раздел страницы" },
  { level: 4, text: "H4 — подраздел" },
  { level: 5, text: "H5 — мелкий подзаголовок" },
  { level: 6, text: "H6 — самый мелкий" },
] as const;

/** All six levels as the mini-app renders them (`.cms-heading--1…6`). */
export function HeadingLevelsExample() {
  return (
    <>
      {LEVELS.map(({ level, text }) => {
        const Tag = `h${level}` as const;
        return (
          <Tag key={level} className={mock.heading[level]}>
            {text}
          </Tag>
        );
      })}
    </>
  );
}

/** How levels combine on a real page. */
export function HeadingPageExample() {
  return (
    <>
      <h2 className={mock.heading[2]}>Заселение</h2>
      <p className={mock.paragraph}>Порядок заселения для первокурсников.</p>
      <h3 className={mock.heading[3]}>Какие документы нужны</h3>
      <p className={mock.paragraph}>Паспорт, направление, медицинская справка.</p>
      <h4 className={mock.heading[4]}>Для иностранных студентов</h4>
      <p className={mock.paragraph}>Дополнительно — миграционная карта.</p>
    </>
  );
}

export function ParagraphExample() {
  return (
    <>
      <p className={mock.paragraph}>
        Заселение проходит <b>с 25 по 31 августа</b> по <i>графику факультета</i>. <u>Опоздавшие</u>{" "}
        заселяются <s>в любой день</s> по согласованию.
      </p>
      <ul className={mock.list}>
        <li>паспорт;</li>
        <li>направление на заселение;</li>
      </ul>
      <ol className={mock.list}>
        <li>получите направление;</li>
        <li>придите в общежитие.</li>
      </ol>
      <p className={mock.paragraph}>
        Подробнее — на <span className={mock.contactLink}>сайте университета</span>.
      </p>
    </>
  );
}

const TONES = [
  { tone: "info", title: "Информация", text: "Справки выдаются в течение 3 рабочих дней." },
  { tone: "warning", title: "Предупреждение", text: "Оплата за сентябрь — до 10 числа." },
  { tone: "success", title: "Успех", text: "Приём заявок открыт." },
  { tone: "danger", title: "Ошибка", text: "Курение в общежитии запрещено." },
] as const;

export function CalloutExample() {
  return (
    <>
      {TONES.map((item) => (
        <aside key={item.tone} className={`${mock.callout} ${mock.calloutTone[item.tone]}`}>
          <b className={mock.calloutTitle}>{item.title}</b>
          {item.text}
        </aside>
      ))}
    </>
  );
}
