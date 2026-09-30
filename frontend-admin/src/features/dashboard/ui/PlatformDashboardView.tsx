import { useMemo, useState } from "react";

import type {
  BotComparison,
  PlatformDashboard,
} from "@/features/dashboard/api/types";
import {
  formatDuration,
  formatPercent,
} from "@/features/dashboard/model/format";
import { dashboardLabels } from "@/features/dashboard/model/labels";
import {
  PlatformTrendChart,
  RankingChart,
} from "@/features/dashboard/ui/DashboardCharts";
import { DashboardEmpty } from "@/features/dashboard/ui/DashboardState";
import { KpiCard } from "@/features/dashboard/ui/KpiCard";

type RankingMetric =
  | "active_users"
  | "submissions"
  | "content_interactions"
  | "capability_uses"
  | "open_tickets"
  | "campaign_link_opens";
type DurationKey = "avg_response_seconds" | "avg_new_to_done_seconds";
type SortKey = RankingMetric | "conversion_rate" | DurationKey;

const DURATION_KEYS: ReadonlySet<SortKey> = new Set<SortKey>([
  "avg_response_seconds",
  "avg_new_to_done_seconds",
]);

function compareBots(key: SortKey) {
  return (left: BotComparison, right: BotComparison) => {
    if (!DURATION_KEYS.has(key)) return right[key] - left[key];
    const a = left[key] || Number.POSITIVE_INFINITY;
    const b = right[key] || Number.POSITIVE_INFINITY;
    return a === b ? 0 : a < b ? -1 : 1;
  };
}

const metricLabels: Record<RankingMetric, string> = {
  active_users: "Активные пользователи",
  submissions: dashboardLabels.submittedForms,
  content_interactions: dashboardLabels.contentInteractions,
  capability_uses: "Использование возможностей",
  open_tickets: dashboardLabels.openRequests,
  campaign_link_opens: "Переходы по кампаниям",
};

export function PlatformDashboardView({
  data,
  onOpenBot,
}: {
  data: PlatformDashboard;
  onOpenBot: (slug: string) => void;
}) {
  const [rankingMetric, setRankingMetric] =
    useState<RankingMetric>("active_users");
  const [trendMetric, setTrendMetric] = useState<
    "active_users" | "submissions"
  >("active_users");
  const [sortKey, setSortKey] = useState<SortKey>("active_users");
  const rows = useMemo(
    () => [...data.bots].sort(compareBots(sortKey)),
    [data.bots, sortKey],
  );
  const rankingRows = useMemo(
    () =>
      [...data.bots]
        .sort((left, right) => right[rankingMetric] - left[rankingMetric])
        .slice(0, 12),
    [data.bots, rankingMetric],
  );
  const current = data.summary;
  const previous = data.previous_summary;

  return (
    <div className="dashboard-stack">
      <section className="dashboard-kpi-grid">
        <KpiCard label="Боты" value={current.bots} hint="Экземпляры в выборке дашборда" />
        <KpiCard label="Уникальная аудитория" value={current.active_users} current={current.active_users} previous={previous.active_users} />
        <KpiCard label="Новые люди" value={current.new_people} current={current.new_people} previous={previous.new_people} />
        <KpiCard label="Новые подключения" value={current.new_memberships} current={current.new_memberships} previous={previous.new_memberships} hint="Регистрации в ботах" />
        <KpiCard label="Используют несколько ботов" value={current.cross_bot_users} current={current.cross_bot_users} previous={previous.cross_bot_users} />
        <KpiCard label={dashboardLabels.submittedForms} value={current.submissions} current={current.submissions} previous={previous.submissions} />
        <KpiCard label="Конверсия аудитории" value={formatPercent(current.conversion_rate)} hint={`${current.submitters} уникальных заявителей`} />
        <KpiCard label={dashboardLabels.openRequests} value={current.open_tickets} current={current.open_tickets} previous={previous.open_tickets} />
        <KpiCard label="Среднее время ответа" value={formatDuration(current.avg_response_seconds)} />
        <KpiCard
          label="Время готовности заявки"
          value={formatDuration(current.avg_new_to_done_seconds)}
          hint="От подачи до статуса «Готова»"
        />
        <KpiCard
          label="Переходы по кампаниям"
          value={current.campaign_link_opens}
          current={current.campaign_link_opens}
          previous={previous.campaign_link_opens}
        />
        <KpiCard
          label="Уникальные переходы"
          value={current.campaign_link_unique_opens}
          current={current.campaign_link_unique_opens}
          previous={previous.campaign_link_unique_opens}
        />
        <KpiCard
          label="Повторные переходы в бота"
          value={current.campaign_link_repeat_opens}
          hint="Всего, без разбивки по периоду — счётчик без временных меток"
        />
        <KpiCard
          label="Несопоставленные переходы"
          value={current.campaign_link_unmatched_opens}
          current={current.campaign_link_unmatched_opens}
          previous={previous.campaign_link_unmatched_opens}
        />
      </section>

      <section className="dashboard-chart-grid">
        <section className="card dashboard-panel">
          <div className="card-head dashboard-panel-head">
            <div><h2 className="card-title">Где больше</h2><p className="card-sub">Рейтинг ботов по выбранному показателю</p></div>
            <select className="select dashboard-metric-select" value={rankingMetric} onChange={(event) => setRankingMetric(event.target.value as RankingMetric)}>
              {Object.entries(metricLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
          </div>
          <div className="card-body dashboard-chart-body">
            {rankingRows.length ? <RankingChart labels={rankingRows.map((item) => item.name)} values={rankingRows.map((item) => item[rankingMetric])} /> : <DashboardEmpty>Боты пока не созданы</DashboardEmpty>}
          </div>
        </section>
        <section className="card dashboard-panel">
          <div className="card-head dashboard-panel-head">
            <div><h2 className="card-title">Динамика по ботам</h2><p className="card-sub">Все боты, включённые в дашборд, в том числе без активности за период</p></div>
            <div className="pill-tabs"><button type="button" className={trendMetric === "active_users" ? "active" : ""} onClick={() => setTrendMetric("active_users")}>Пользователи</button><button type="button" className={trendMetric === "submissions" ? "active" : ""} onClick={() => setTrendMetric("submissions")}>{dashboardLabels.formsShort}</button></div>
          </div>
          <div className="card-body dashboard-chart-body">
            {data.trend.length ? <PlatformTrendChart points={data.trend} bots={data.bots} metric={trendMetric} /> : <DashboardEmpty>За период активности не было</DashboardEmpty>}
          </div>
        </section>
      </section>

      <section className="card dashboard-panel">
        <div className="card-head dashboard-panel-head">
          <div><h2 className="card-title">Сравнение ботов</h2><p className="card-sub">Нажмите название, чтобы открыть детальную статистику бота</p></div>
          <label className="dashboard-sort"><span>Сортировка</span><select className="select" value={sortKey} onChange={(event) => setSortKey(event.target.value as SortKey)}><option value="active_users">Пользователи</option><option value="submissions">{dashboardLabels.formsShort}</option><option value="conversion_rate">Конверсия</option><option value="content_interactions">{dashboardLabels.contentInteractionsShort}</option><option value="capability_uses">Возможности</option><option value="open_tickets">{dashboardLabels.requestsShort}</option><option value="campaign_link_opens">Переходы по кампаниям</option><option value="avg_response_seconds">Время ответа</option><option value="avg_new_to_done_seconds">Время готовности</option></select></label>
        </div>
        <div className="dashboard-table-wrap">
          <table className="dashboard-table dashboard-comparison-table">
            <thead><tr><th>Бот</th><th>Пользователи</th><th>{dashboardLabels.formsShort}</th><th>Конверсия</th><th>{dashboardLabels.contentInteractionsShort}</th><th>Возможности</th><th>{dashboardLabels.requestsShort}</th><th>Переходы</th><th>Ответ</th><th>Готовность</th></tr></thead>
            <tbody>
              {rows.map((item) => <ComparisonRow key={item.bot_id} item={item} onOpen={() => onOpenBot(item.slug)} />)}
              {!rows.length ? <tr><td colSpan={10}><DashboardEmpty>Боты пока не созданы</DashboardEmpty></td></tr> : null}
            </tbody>
          </table>
        </div>
      </section>

      <p className="dashboard-freshness">
        Сформировано {new Date(data.generated_at).toLocaleString("ru-RU")}.
      </p>
    </div>
  );
}

function ComparisonRow({ item, onOpen }: { item: BotComparison; onOpen: () => void }) {
  return (
    <tr>
      <td data-label="Бот"><button type="button" className="dashboard-bot-link" onClick={onOpen}><strong>{item.name}</strong><small>{item.slug}</small></button></td>
      <td data-label="Пользователи">{item.active_users}</td>
      <td data-label={dashboardLabels.formsShort}>{item.submissions}</td>
      <td data-label="Конверсия">{formatPercent(item.conversion_rate)}</td>
      <td data-label={dashboardLabels.contentInteractionsShort}>{item.content_interactions}</td>
      <td data-label="Возможности">{item.capability_uses}</td>
      <td data-label={dashboardLabels.requestsShort}>{item.open_tickets}</td>
      <td data-label="Переходы">{item.campaign_link_opens}</td>
      <td data-label="Ответ">{formatDuration(item.avg_response_seconds)}</td>
      <td data-label="Готовность">{formatDuration(item.avg_new_to_done_seconds)}</td>
    </tr>
  );
}
