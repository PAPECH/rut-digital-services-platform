import * as mock from "../../shared/MiniAppMock/MiniAppMock.css";

const CONTACTS = [
  { label: "Телефон", value: "+7 495 000-00-00", link: true },
  { label: "Почта", value: "uvp@example.ru", link: true },
  { label: "Кабинет", value: "ауд. 1234", link: false },
];

export function ContactListExample() {
  return (
    <>
      <h3 className={mock.heading[3]}>Куда обращаться</h3>
      {CONTACTS.map((item) => (
        <div key={item.label} className={mock.contactRow}>
          <span className={mock.contactLabel}>{item.label}</span>
          <span className={item.link ? mock.contactLink : mock.contactValue}>{item.value}</span>
        </div>
      ))}
    </>
  );
}

export function LinkButtonExample() {
  return (
    <div className={`${mock.link} ${mock.linkStyle.button}`}>
      <span>Личный кабинет студента</span>
      <span aria-hidden>→</span>
    </div>
  );
}

export function LinkCardExample() {
  return (
    <div className={`${mock.link} ${mock.linkStyle.card}`}>
      <span>ул. Образцова, д. 9 — на карте</span>
      <span aria-hidden>→</span>
    </div>
  );
}
