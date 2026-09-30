import { useState } from "react";

import { InteractiveBadge } from "../InteractiveBadge/InteractiveBadge";
import { changed, hotspot } from "../motion.css";
import * as styles from "./GuideInteractionHint.css";

const STORAGE_KEY = "admin-guide:interaction-hint-dismissed";

function readDismissed(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

/**
 * One-time legend explaining what in the guide reacts to clicks. Dismissal is a per-viewer
 * convenience in `localStorage`; if storage is unavailable the hint simply shows again.
 */
export function GuideInteractionHint() {
  const [dismissed, setDismissed] = useState(readDismissed);
  if (dismissed) return null;

  const dismiss = () => {
    setDismissed(true);
    try {
      window.localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // Storage blocked — the hint just reappears next visit.
    }
  };

  return (
    <aside className={styles.hint} aria-label="Как пользоваться инструкцией">
      <span className={styles.icon} aria-hidden>
        💡
      </span>
      <div className={styles.content}>
        <p className={styles.title}>Как пользоваться инструкцией</p>
        <ul className={styles.list}>
          <li className={styles.row}>
            <InteractiveBadge />
            <span>
              Демонстрация или макет телефона с этим значком реагирует на нажатия: шаги, «Далее»,
              кнопки, карточки, аккордеон, вкладки.
            </span>
          </li>
          <li className={styles.row}>
            <span className={`${styles.ringSample} ${hotspot}`}>Сохранить</span>
            <span>Синяя обводка — нажмите сюда на этом шаге.</span>
          </li>
          <li className={styles.row}>
            <span className={`${styles.ringSample} ${changed}`}>Изменилось</span>
            <span>Жёлтая заливка — что изменилось на этом шаге. Нажимать не нужно.</span>
          </li>
          <li className={styles.row}>
            <span className={styles.staticSample}>Без значка</span>
            <span>Просто картинка-пример: так это выглядит у пользователя, нажимать не нужно.</span>
          </li>
        </ul>
      </div>
      <button type="button" className="btn btn-primary btn-sm" onClick={dismiss}>
        Понятно
      </button>
    </aside>
  );
}
