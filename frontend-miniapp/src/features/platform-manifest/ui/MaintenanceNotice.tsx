import type { MaintenancePolicy } from "@/api/types";

export function MaintenanceNotice({ policy }: { policy: MaintenancePolicy }) {
  return (
    <aside
      className={`maintenance-notice maintenance-notice--${policy.mode}`}
      role="status"
    >
      <b>{policy.title || "Технические работы"}</b>
      {policy.message ? <span>{policy.message}</span> : null}
    </aside>
  );
}

export function MaintenanceScreen({ policy }: { policy: MaintenancePolicy }) {
  return (
    <main className="maintenance-screen">
      <div className="maintenance-screen__card">
        <div className="maintenance-screen__icon" aria-hidden="true">
          🛠️
        </div>
        <h1>{policy.title || "Ведутся технические работы"}</h1>
        <p>
          {policy.message ||
            "Пожалуйста, попробуйте открыть приложение позднее."}
        </p>
      </div>
    </main>
  );
}
