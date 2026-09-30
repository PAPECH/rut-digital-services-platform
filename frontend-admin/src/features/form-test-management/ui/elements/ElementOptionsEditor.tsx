import type { FormTestOption } from "@/entities/form-test/model/types";
import * as styles from "./ElementOptionsEditor.css";

function nextOptionValue(options: FormTestOption[]): string {
  const used = new Set(options.map((option) => option.value));
  let index = options.length + 1;
  let value = String(index);
  while (used.has(value)) {
    index += 1;
    value = String(index);
  }
  return value;
}

export function ElementOptionsEditor({
  options,
  onChange,
}: {
  options: FormTestOption[];
  onChange: (options: FormTestOption[]) => void;
}) {
  const replace = (index: number, option: FormTestOption) =>
    onChange(options.map((item, current) => (current === index ? option : item)));

  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= options.length) return;
    const next = [...options];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.head}>
        <span>Варианты ответа</span>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          onClick={() =>
            onChange([
              ...options,
              { value: nextOptionValue(options), label: "", score: 0 },
            ])
          }
        >
          + вариант
        </button>
      </div>
      {options.length === 0 && (
        <div className={styles.empty}>Нет вариантов — добавьте хотя бы один</div>
      )}
      {options.map((option, index) => (
        <div className={styles.row} key={index}>
          <input
            className="input"
            aria-label="Значение варианта"
            placeholder="значение"
            value={option.value}
            onChange={(event) => replace(index, { ...option, value: event.target.value })}
          />
          <input
            className="input"
            aria-label="Текст варианта"
            placeholder="текст варианта"
            value={option.label}
            onChange={(event) => replace(index, { ...option, label: event.target.value })}
          />
          <input
            className="input"
            aria-label="Балл варианта"
            type="number"
            placeholder="балл"
            value={option.score}
            onChange={(event) =>
              replace(index, { ...option, score: Number(event.target.value) || 0 })
            }
          />
          <div className={styles.actions}>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled={index === 0}
              onClick={() => move(index, -1)}
              aria-label="Поднять вариант"
            >
              ↑
            </button>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              disabled={index === options.length - 1}
              onClick={() => move(index, 1)}
              aria-label="Опустить вариант"
            >
              ↓
            </button>
            <button
              type="button"
              className="btn btn-danger btn-sm"
              onClick={() => onChange(options.filter((_, current) => current !== index))}
            >
              Удалить
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
