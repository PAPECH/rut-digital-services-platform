import * as mock from "./MiniAppMock.css";

/** `.card.service-form-card.cms-form-action` — «Переход к форме / к тесту», form and test catalogs. */
export function MockActionCard({ title, description }: { title: string; description?: string }) {
  return (
    <div className={mock.actionCard}>
      <span className={mock.actionText}>
        <span className={mock.actionTitle}>{title}</span>
        {description ? <span className={mock.actionDescription}>{description}</span> : null}
      </span>
      <span className={mock.actionChevron} aria-hidden>
        ›
      </span>
    </div>
  );
}
