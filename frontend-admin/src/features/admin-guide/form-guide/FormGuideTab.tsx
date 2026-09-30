import { GuideSection } from "../shared/GuideSection/GuideSection";
import { GuideTabLayout } from "../shared/GuideTabLayout/GuideTabLayout";
import { FieldCreationDemo } from "./FieldCreationDemo/FieldCreationDemo";
import { FieldTypeCatalog } from "./FieldTypeCatalog/FieldTypeCatalog";
import { ProfileDuplicationWarning } from "./ProfileDuplicationWarning/ProfileDuplicationWarning";
import * as styles from "./FormGuideTab.css";

const SECTIONS = [
  { id: "forms-create", title: "Как создать форму и поле" },
  { id: "forms-profile", title: "Данные профиля" },
  { id: "forms-types", title: "Типы полей" },
] as const;

export function FormGuideTab() {
  return (
    <GuideTabLayout tab="forms" sections={SECTIONS}>
      <GuideSection
        {...SECTIONS[0]}
        lead="Раздел «Конструктор форм» доступен администраторам бота. Форма — это список полей-вопросов; пользователь заполняет её в мини-приложении, а ответы приходят в раздел «Формы»."
      >
        <FieldCreationDemo />
        <ul className={styles.notes}>
          <li>
            <b>Активное</b> — снимите галочку, чтобы скрыть поле, не удаляя его: старые ответы в
            заявках сохранятся.
          </li>
          <li>
            <b>Стабильный ключ</b> — техническое имя поля, по нему связываются ответы в заявках и
            выгрузках. У опубликованной формы не меняйте.
          </li>
          <li>
            <b>Подставлять из поля профиля</b> — ключ поля профиля (например, email): значение
            подставится автоматически.
          </li>
        </ul>
      </GuideSection>
      <GuideSection {...SECTIONS[1]}>
        <ProfileDuplicationWarning />
      </GuideSection>
      <GuideSection
        {...SECTIONS[2]}
        lead="Названия — как в меню «Добавить поле…». Под описанием — как поле выглядит в форме."
      >
        <FieldTypeCatalog />
      </GuideSection>
    </GuideTabLayout>
  );
}
