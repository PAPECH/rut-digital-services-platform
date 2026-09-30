import * as mock from "../../shared/MiniAppMock/MiniAppMock.css";
import { MockFaqItem } from "../../shared/MiniAppMock/MockFaqItem";
import { MockPhoto } from "../../shared/MiniAppMock/MockPhoto";
import { MockTile } from "../../shared/MiniAppMock/MockTile";
import * as styles from "./DynamicBlockExamples.css";

export function FaqListExample() {
  return (
    <>
      <h3 className={mock.sectionLabel}>Частые вопросы</h3>
      <MockFaqItem
        question="Можно ли жить с питомцем?"
        answer="Нет, содержание животных в общежитии запрещено."
      />
      <MockFaqItem
        question="Когда меняют постельное бельё?"
        answer="Раз в неделю, по графику на этаже."
      />
    </>
  );
}

export function NewsListExample() {
  return (
    <div className={mock.newsCard}>
      <MockPhoto className={styles.cover} />
      <div className={mock.newsBody}>
        <div className={mock.newsTitle}>Открыт приём заявок на переселение</div>
        <div className={mock.newsExcerpt}>Подать заявку можно до 15 октября в мини-приложении.</div>
        <div className={mock.newsFooter}>
          <span className={mock.newsCategory}>Общежитие</span>
          <span className={mock.newsDate}>28.09.2026</span>
        </div>
      </div>
    </div>
  );
}

/** Rendered as a category card (`.cms-category-card`) with the capability's icon. */
export function CapabilityActionExample() {
  return <MockTile title="Расписание занятий" subtitle="Выберите группу и неделю" icon="🗓" />;
}
