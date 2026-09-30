import * as mock from "../../shared/MiniAppMock/MiniAppMock.css";
import { MockActionCard } from "../../shared/MiniAppMock/MockActionCard";
import { MockSubCard } from "../../shared/MiniAppMock/MockSubCard";

export function FormActionExample() {
  return (
    <MockActionCard
      title="Заявка на ремонт"
      description="Сломалась мебель, сантехника или электрика"
    />
  );
}

export function FormCatalogExample() {
  return (
    <>
      <h3 className={mock.sectionLabel}>Доступные формы</h3>
      <MockActionCard title="Заявка на ремонт" description="Мебель, сантехника, электрика" />
      <MockActionCard title="Заказ справки" description="О проживании в общежитии" />
      <MockActionCard title="Жалоба или предложение" />
    </>
  );
}

export function SubmissionHistoryExample() {
  return (
    <>
      <h3 className={mock.sectionLabel}>Мои обращения</h3>
      <MockSubCard
        name="Заявка на ремонт #128"
        meta="Создана 12.09.2026, 14:30"
        status="В работе"
        tone="work"
      />
      <MockSubCard
        name="Заказ справки #97"
        meta="Создана 03.09.2026, 10:05"
        status="Завершено"
        tone="done"
      />
    </>
  );
}

export function TestActionExample() {
  return <MockActionCard title="Правила проживания" description="10 вопросов · около 5 минут" />;
}

export function TestCatalogExample() {
  return (
    <>
      <h3 className={mock.sectionLabel}>Тесты</h3>
      <MockActionCard title="Правила проживания" />
      <MockActionCard title="Пожарная безопасность" />
    </>
  );
}

export function TestAttemptHistoryExample() {
  return (
    <>
      <h3 className={mock.sectionLabel}>Мои результаты</h3>
      <MockSubCard
        name="Правила проживания"
        meta="Создана 20.09.2026, 18:12"
        status="Завершён"
        tone="done"
      />
      <MockSubCard
        name="Пожарная безопасность"
        meta="Создана 21.09.2026, 09:40"
        status="В процессе"
        tone="new"
      />
    </>
  );
}
