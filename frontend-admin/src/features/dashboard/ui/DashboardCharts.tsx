import { Bar, Line } from "react-chartjs-2";
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Tooltip,
} from "chart.js";

import type {
  BotComparison,
  BotTrendPoint,
  FunnelStep,
  PlatformTrendPoint,
  TicketTrendPoint,
} from "@/features/dashboard/api/types";
import { DASHBOARD_COLORS } from "@/features/dashboard/model/format";
import { dashboardLabels } from "@/features/dashboard/model/labels";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Filler,
  Tooltip,
  Legend,
);

const lineOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: "index" as const, intersect: false },
  scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
};

export function BotTrendChart({ points }: { points: BotTrendPoint[] }) {
  return (
    <Line
      options={lineOptions}
      data={{
        labels: points.map((item) => item.day),
        datasets: [
          {
            label: "Активные пользователи",
            data: points.map((item) => item.active_users),
            borderColor: DASHBOARD_COLORS[0],
            backgroundColor: "rgba(27,54,93,.12)",
            fill: true,
            tension: 0.3,
          },
          {
            label: dashboardLabels.formsShort,
            data: points.map((item) => item.submissions),
            borderColor: DASHBOARD_COLORS[2],
            backgroundColor: "rgba(46,139,87,.10)",
            tension: 0.3,
          },
        ],
      }}
    />
  );
}

export function FunnelChart({ steps }: { steps: FunnelStep[] }) {
  return (
    <Bar
      options={{
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
      }}
      data={{
        labels: steps.map((item) => item.label),
        datasets: [
          {
            label: "Уникальные пользователи",
            data: steps.map((item) => item.unique_users),
            backgroundColor: DASHBOARD_COLORS[1],
            borderRadius: 7,
          },
        ],
      }}
    />
  );
}

export function TicketTrendChart({ points }: { points: TicketTrendPoint[] }) {
  return (
    <Line
      options={lineOptions}
      data={{
        labels: points.map((item) => item.day),
        datasets: [
          {
            label: "Входящие",
            data: points.map((item) => item.incoming),
            borderColor: DASHBOARD_COLORS[0],
            tension: 0.3,
          },
          {
            label: "Отвеченные",
            data: points.map((item) => item.answered),
            borderColor: DASHBOARD_COLORS[2],
            tension: 0.3,
          },
        ],
      }}
    />
  );
}

export function PlatformTrendChart({
  points,
  bots,
  metric,
}: {
  points: PlatformTrendPoint[];
  bots: BotComparison[];
  metric: "active_users" | "submissions";
}) {
  const valuesByBotAndDay = new Map<string, number>();
  for (const point of points) {
    valuesByBotAndDay.set(`${point.bot_id}:${point.day}`, point[metric]);
  }
  const days = [...new Set(points.map((item) => item.day))].sort();
  const datasets = bots.map((bot, index) => {
    const color = `hsl(${Math.round((index * 360) / Math.max(bots.length, 1))} 62% 43%)`;
    return {
      label: bot.name,
      data: days.map((day) => valuesByBotAndDay.get(`${bot.bot_id}:${day}`) ?? 0),
      borderColor: color,
      backgroundColor: color,
      tension: 0.3,
    };
  });
  return (
    <div className="dashboard-platform-trend">
      <div className="dashboard-platform-trend__canvas">
        <Line
          options={{
            ...lineOptions,
            plugins: { legend: { display: false } },
          }}
          data={{ labels: days, datasets }}
        />
      </div>
      <div className="dashboard-platform-trend__legend" aria-label="Боты на графике">
        {datasets.map((dataset, index) => (
          <span key={bots[index].bot_id}>
            <i style={{ backgroundColor: dataset.borderColor }} />
            {dataset.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export function RankingChart({
  labels,
  values,
}: {
  labels: string[];
  values: number[];
}) {
  return (
    <Bar
      options={{
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
      }}
      data={{
        labels,
        datasets: [
          {
            label: "Значение",
            data: values,
            backgroundColor: DASHBOARD_COLORS[1],
            borderRadius: 7,
          },
        ],
      }}
    />
  );
}
