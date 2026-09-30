import type { TestDraft } from "@/entities/form-test/model/types";
import * as styles from "./AttemptSettingsSection.css";

export function AttemptSettingsSection({
  draft,
  onChange,
}: {
  draft: TestDraft;
  onChange: (patch: Partial<TestDraft>) => void;
}) {
  return (
    <div>
      <h3>Настройки прохождения</h3>
      <div className={styles.list}>
        <div>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={draft.allow_retake}
              onChange={(event) => onChange({ allow_retake: event.target.checked })}
            />
            <span>Разрешить повторное прохождение</span>
          </label>
          <p className={styles.hint}>
            Студент, уже прошедший тест, увидит свой прошлый результат и кнопку «Пройти заново».
            Без этой настройки — только прошлый результат, без возможности пройти повторно.
          </p>
        </div>

        <div>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={draft.show_attempt_history}
              onChange={(event) => onChange({ show_attempt_history: event.target.checked })}
            />
            <span>Показывать историю попыток студенту</span>
          </label>
          <p className={styles.hint}>Управляет тем, попадает ли этот тест в общий список пройденных тестов студента.</p>
        </div>

        <div>
          <label className={styles.toggle}>
            <input
              type="checkbox"
              checked={draft.show_scores}
              onChange={(event) => onChange({ show_scores: event.target.checked })}
            />
            <span>Показывать баллы за ответы</span>
          </label>
          <p className={styles.hint}>
            Текст интерпретации виден студенту всегда; эта настройка добавляет к нему числовые
            значения по шкалам.
          </p>
        </div>
      </div>
    </div>
  );
}
