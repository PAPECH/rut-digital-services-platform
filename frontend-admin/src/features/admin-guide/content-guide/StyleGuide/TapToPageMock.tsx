import { useState, type ReactNode } from "react";

import * as mock from "../../shared/MiniAppMock/MiniAppMock.css";
import { MockTile } from "../../shared/MiniAppMock/MockTile";
import { hotspot } from "../../shared/motion.css";
import { PhoneMockup } from "../../shared/PhoneMockup/PhoneMockup";
import * as styles from "./StyleGuide.css";

/**
 * Tappable phone: the menu with a highlighted card; tapping it opens `page`, «← Назад» returns.
 * Good and bad variants differ only in `page`.
 */
export function TapToPageMock({ tileTitle, page }: { tileTitle: string; page: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={styles.tapDemo}>
      <PhoneMockup title={open ? tileTitle : "Главное меню"} interactive>
        {open ? (
          <div className={styles.pageEnter}>
            <button type="button" className={styles.back} onClick={() => setOpen(false)}>
              ← Назад
            </button>
            {page}
          </div>
        ) : (
          <div className={mock.grid}>
            <MockTile
              title={tileTitle}
              subtitle="Документы и сроки"
              icon="⌂"
              className={hotspot}
              onClick={() => setOpen(true)}
            />
            <MockTile title="Оплата проживания" subtitle="Тарифы и реквизиты" icon="₽" />
          </div>
        )}
      </PhoneMockup>
      <span className={styles.tapHint}>
        {open ? "Сравните заголовок с карточкой" : `Нажмите на карточку «${tileTitle}»`}
      </span>
    </div>
  );
}
