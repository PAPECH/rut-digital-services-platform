import type {
  DashboardFilters as DashboardFilterValue,
  DashboardScope,
} from "@/features/dashboard/api/types";

export function DashboardFilters({
  platformAdmin,
  scope,
  filters,
  onScope,
  onDays,
  onDateFrom,
  onDateTo,
}: {
  platformAdmin: boolean;
  scope: DashboardScope;
  filters: DashboardFilterValue;
  onScope: (scope: DashboardScope) => void;
  onDays: (days: 7 | 30 | 90) => void;
  onDateFrom: (value: string) => void;
  onDateTo: (value: string) => void;
}) {
  return (
    <div className="dashboard-controls">
      {platformAdmin ? (
        <div className="pill-tabs" aria-label="Масштаб статистики">
          <button
            type="button"
            className={scope === "platform" ? "active" : ""}
            onClick={() => onScope("platform")}
          >
            Вся платформа
          </button>
          <button
            type="button"
            className={scope === "bot" ? "active" : ""}
            onClick={() => onScope("bot")}
          >
            Выбранный бот
          </button>
        </div>
      ) : null}
      <div className="dashboard-period-controls">
        <div className="pill-tabs" aria-label="Период статистики">
          {([7, 30, 90] as const).map((days) => (
            <button
              type="button"
              key={days}
              className={
                !filters.dateFrom && !filters.dateTo && filters.days === days
                  ? "active"
                  : ""
              }
              onClick={() => onDays(days)}
            >
              {days === 7 ? "Неделя" : days === 30 ? "Месяц" : "Квартал"}
            </button>
          ))}
        </div>
        <div className="date-range">
          <input
            className="date-input"
            type="date"
            aria-label="Начало периода"
            value={filters.dateFrom}
            onChange={(event) => onDateFrom(event.target.value)}
          />
          <span className="date-separator">—</span>
          <input
            className="date-input"
            type="date"
            aria-label="Конец периода"
            value={filters.dateTo}
            min={filters.dateFrom || undefined}
            onChange={(event) => onDateTo(event.target.value)}
          />
        </div>
      </div>
    </div>
  );
}
