import type { FormTestElement, ResultScale } from "@/entities/form-test/model/types";
import { ResultScaleRow } from "./ResultScaleRow";
import * as styles from "./ResultScaleListEditor.css";

function nextScaleKey(scales: ResultScale[]): string {
  const used = new Set(scales.map((scale) => scale.key));
  let index = scales.length + 1;
  let key = `scale_${index}`;
  while (used.has(key)) {
    index += 1;
    key = `scale_${index}`;
  }
  return key;
}

export function ResultScaleListEditor({
  elements,
  resultScales,
  onChange,
}: {
  elements: FormTestElement[];
  resultScales: ResultScale[];
  onChange: (resultScales: ResultScale[]) => void;
}) {
  const scoringKeys = elements
    .map((element) => element.scoring_key)
    .filter((key): key is string => Boolean(key));

  const replace = (index: number, scale: ResultScale) =>
    onChange(resultScales.map((item, current) => (current === index ? scale : item)));
  const move = (index: number, direction: -1 | 1) => {
    const target = index + direction;
    if (target < 0 || target >= resultScales.length) return;
    const next = [...resultScales];
    [next[index], next[target]] = [next[target], next[index]];
    onChange(next);
  };

  return (
    <div>
      <div className={styles.head}>
        <div>
          <h3>Расчётные шкалы ({resultScales.length})</h3>
          <span className={styles.hint}>
            Публикация теста требует хотя бы одну шкалу — черновик можно сохранять и без неё
          </span>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() =>
            onChange([
              ...resultScales,
              {
                key: nextScaleKey(resultScales),
                label: "",
                terms: [],
                constant: 0,
                aggregation: "sum",
              },
            ])
          }
        >
          + шкала
        </button>
      </div>
      {resultScales.length ? (
        <div className={styles.list}>
          {resultScales.map((scale, index) => (
            <ResultScaleRow
              key={`${scale.key}-${index}`}
              scale={scale}
              index={index}
              isFirst={index === 0}
              isLast={index === resultScales.length - 1}
              scoringKeys={scoringKeys}
              otherScaleKeys={resultScales
                .map((item) => item.key)
                .filter((key) => key !== scale.key)}
              onChange={(updated) => replace(index, updated)}
              onMove={(direction) => move(index, direction)}
              onDelete={() => onChange(resultScales.filter((_, current) => current !== index))}
            />
          ))}
        </div>
      ) : (
        <div className={styles.empty}>Пока нет расчётных шкал</div>
      )}
    </div>
  );
}
