export function DashboardLoading() {
  return (
    <div className="dashboard-kpi-grid" aria-label="Загрузка статистики">
      {Array.from({ length: 8 }, (_, index) => (
        <div className="card dashboard-kpi" key={index}>
          <span className="skeleton" style={{ width: "55%", height: 13 }} />
          <span className="skeleton" style={{ width: "35%", height: 30 }} />
        </div>
      ))}
    </div>
  );
}

export function DashboardError({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div className="card dashboard-state">
      <strong>Статистика временно недоступна</strong>
      <p>{message}</p>
      <button type="button" className="btn btn-primary" onClick={onRetry}>
        Повторить
      </button>
    </div>
  );
}

export function DashboardEmpty({ children }: { children: React.ReactNode }) {
  return <div className="dashboard-empty">{children}</div>;
}
