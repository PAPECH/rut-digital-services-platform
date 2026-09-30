import { formatDelta } from "@/features/dashboard/model/format";

export function KpiCard({
  label,
  value,
  current,
  previous,
  hint,
}: {
  label: string;
  value: string | number;
  current?: number;
  previous?: number;
  hint?: string;
}) {
  const delta =
    current === undefined || previous === undefined
      ? null
      : formatDelta(current, previous);
  return (
    <article className="dashboard-kpi card">
      <div className="dashboard-kpi__head">
        <span>{label}</span>
        {delta ? (
          <span
            className={`dashboard-delta ${current! >= previous! ? "is-up" : "is-down"}`}
            title="Изменение к предыдущему аналогичному периоду"
          >
            {delta}
          </span>
        ) : null}
      </div>
      <strong>{value}</strong>
      {hint ? <small>{hint}</small> : null}
    </article>
  );
}
