import { useState } from "react";

import * as mock from "../../shared/MiniAppMock/MiniAppMock.css";
import { MockFaqItem } from "../../shared/MiniAppMock/MockFaqItem";
import { MockTile } from "../../shared/MiniAppMock/MockTile";

/** Tap an item to open it — same as in the mini-app. */
export function AccordionExample() {
  return (
    <div className={mock.grid}>
      <MockFaqItem
        question="Льготное заселение"
        answer="Для отдельных категорий студентов — вне очереди."
      />
      <MockFaqItem
        question="Заселение иностранных студентов"
        answer="Дополнительно нужна миграционная карта."
      />
    </div>
  );
}

const STEPS = [
  { title: "Получите направление", text: "В деканате или в личном кабинете." },
  { title: "Пройдите медосмотр", text: "В поликлинике университета." },
  { title: "Придите в общежитие", text: "С паспортом и направлением." },
];

export function StepsExample() {
  return (
    <ol className={mock.steps}>
      {STEPS.map((item, index) => (
        <li key={item.title} className={mock.stepRow}>
          <span className={mock.stepNumber}>{index + 1}</span>
          <div>
            <strong className={mock.stepTitle}>{item.title}</strong>
            <p className={mock.paragraph}>{item.text}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}

const TABS = [
  { title: "Бюджет", text: "Проживание оплачивается по льготному тарифу." },
  { title: "Платное", text: "Проживание оплачивается по договору." },
];

/** Tap a tab to switch — same as in the mini-app. */
export function TabsExample() {
  const [active, setActive] = useState(0);
  return (
    <>
      <div className={mock.tabs} role="tablist">
        {TABS.map((tab, index) => (
          <button
            key={tab.title}
            type="button"
            role="tab"
            aria-selected={index === active}
            className={`${mock.tab} ${index === active ? mock.tabActive : ""}`}
            onClick={() => setActive(index)}
          >
            {tab.title}
          </button>
        ))}
      </div>
      <p className={mock.paragraph}>{TABS[active].text}</p>
    </>
  );
}

export function CategoryGridExample() {
  return (
    <div className={mock.grid}>
      <MockTile title="Заселение" subtitle="Документы и сроки" icon="⌂" />
      <MockTile title="Оплата проживания" subtitle="Тарифы и реквизиты" icon="₽" filled />
      <MockTile title="Общежитие № 1" subtitle="ул. Образцова, д. 9" image />
    </div>
  );
}
