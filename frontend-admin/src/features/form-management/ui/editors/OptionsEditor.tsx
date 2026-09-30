import type { FormOption } from "@/entities/form/model/types";
import { EditorField } from "./EditorFields";
export function OptionsEditor({
  options,
  onChange,
}: {
  options: FormOption[];
  onChange: (options: FormOption[]) => void;
}) {
  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= options.length) return;
    const next = [...options];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };

  return (
    <div className="content-nested-list">
      <strong>Варианты ответа</strong>
      {options.map((option, index) => (
        <div className="content-inline-row" key={`${index}-${option.value}`}>
          <EditorField label="Значение">
            <input
              className="input"
              placeholder="option_1"
              value={option.value}
              onChange={(e) =>
                onChange(
                  options.map((item, i) =>
                    i === index ? { ...item, value: e.target.value } : item,
                  ),
                )
              }
            />
          </EditorField>
          <EditorField label="Подпись">
            <input
              className="input"
              placeholder="Вариант 1"
              value={option.label}
              onChange={(e) =>
                onChange(
                  options.map((item, i) =>
                    i === index ? { ...item, label: e.target.value } : item,
                  ),
                )
              }
            />
          </EditorField>
          <div className="content-inline-actions">
            <button
              className="btn btn-ghost btn-sm"
              type="button"
              disabled={index === 0}
              onClick={() => move(index, -1)}
              aria-label="Поднять вариант"
            >
              ↑
            </button>
            <button
              className="btn btn-ghost btn-sm"
              type="button"
              disabled={index === options.length - 1}
              onClick={() => move(index, 1)}
              aria-label="Опустить вариант"
            >
              ↓
            </button>
            <button
              className="btn btn-danger btn-sm"
              type="button"
              onClick={() => onChange(options.filter((_, i) => i !== index))}
            >
              Удалить
            </button>
          </div>
        </div>
      ))}
      <button
        className="btn btn-secondary btn-sm"
        type="button"
        onClick={() =>
          onChange([
            ...options,
            {
              value: `option_${options.length + 1}`,
              label: `Вариант ${options.length + 1}`,
            },
          ])
        }
      >
        Добавить вариант
      </button>
    </div>
  );
}
