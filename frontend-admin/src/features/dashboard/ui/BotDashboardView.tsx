import type { BotDashboard } from "@/features/dashboard/api/types";
import {
  formatDuration,
  formatPercent,
} from "@/features/dashboard/model/format";
import { dashboardLabels } from "@/features/dashboard/model/labels";
import {
  BotTrendChart,
  FunnelChart,
  TicketTrendChart,
} from "@/features/dashboard/ui/DashboardCharts";
import { DashboardEmpty } from "@/features/dashboard/ui/DashboardState";
import { KpiCard } from "@/features/dashboard/ui/KpiCard";

const contentKindLabels: Record<string, string> = {
  content_category_open: "Категория",
  content_tab_open: "Вкладка",
  link_open: "Ссылка/карточка",
  accordion_item_open: "Аккордеон",
  contact_open: "Контакт",
  file_download: "Файл",
  form_card_open: "Карточка формы",
  capability_card_open: "Карточка сервиса",
  form_catalog_open: "Каталог форм",
  submission_history_open: "История заявок",
  faq_list_open: "FAQ",
};

export function BotDashboardView({ data }: { data: BotDashboard }) {
  const current = data.summary;
  const previous = data.previous_summary;
  return (
    <div className="dashboard-stack">
      <section className="dashboard-kpi-grid">
        <KpiCard label="Активные пользователи" value={current.active_users} current={current.active_users} previous={previous.active_users} />
        <KpiCard label="Новые пользователи" value={current.new_users} current={current.new_users} previous={previous.new_users} />
        <KpiCard label={dashboardLabels.submittedForms} value={current.submissions} current={current.submissions} previous={previous.submissions} />
        <KpiCard label="Конверсия аудитории" value={formatPercent(current.conversion_rate)} hint={`${current.submitters} уникальных заявителей`} />
        <KpiCard label={dashboardLabels.openRequests} value={current.open_tickets} current={current.open_tickets} previous={previous.open_tickets} />
        <KpiCard label="Среднее время ответа" value={formatDuration(current.avg_response_seconds)} />
        <KpiCard label="До начала работы" value={formatDuration(current.avg_new_to_work_seconds)} />
        <KpiCard label="В работе" value={formatDuration(current.avg_work_to_done_seconds)} />
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
        <DashboardChart title="Активность и отправленные формы" subtitle="Уникальные пользователи и отправленные формы по дням">
          {data.trend.length ? <BotTrendChart points={data.trend} /> : <DashboardEmpty>За период активности не было</DashboardEmpty>}
        </DashboardChart>
        <DashboardChart title="Воронка" subtitle="Уникальные пользователи на каждом этапе">
          {data.funnel.some((item) => item.unique_users) ? <FunnelChart steps={data.funnel} /> : <DashboardEmpty>События воронки ещё не накоплены</DashboardEmpty>}
        </DashboardChart>
      </section>

      <DashboardTable title="Формы" subtitle="Открытия, начало заполнения и успешные отправки">
        <thead><tr><th>Форма</th><th>Открыли</th><th>Начали</th><th>Отправили</th><th>Завершение</th><th>Отклонено</th></tr></thead>
        <tbody>
          {data.forms.map((item) => (
            <tr key={item.form_id}><td data-label="Форма"><strong>{item.name}</strong></td><td data-label="Открыли">{item.opens}</td><td data-label="Начали">{item.starts}</td><td data-label="Отправили">{item.submissions}</td><td data-label="Завершение">{formatPercent(item.completion_rate)}</td><td data-label="Отклонено">{formatPercent(item.rejected_share)}</td></tr>
          ))}
          {!data.forms.length ? <EmptyRow columns={6} text="За период формы не использовались" /> : null}
        </tbody>
      </DashboardTable>

      <DashboardTable title={dashboardLabels.contentInteractions} subtitle="Какие конкретно категории, вкладки и визуальные элементы открывали">
        <thead><tr><th>Категория</th><th>Элемент</th><th>Тип</th><th>Цель</th><th>Действия</th><th>Пользователи</th></tr></thead>
        <tbody>
          {data.content.map((item, index) => (
            <tr key={`${item.content_version_id}:${item.block_id}:${item.item_id}:${item.kind}:${index}`}><td data-label="Категория">{item.category_name}</td><td data-label="Элемент"><strong>{item.label}</strong></td><td data-label="Тип"><span className="status-chip">{contentKindLabels[item.kind] ?? item.kind}</span></td><td data-label="Цель">{item.target_label ?? "—"}</td><td data-label="Действия">{item.total}</td><td data-label="Пользователи">{item.unique_users}</td></tr>
          ))}
          {!data.content.length ? <EmptyRow columns={6} text="Клики по категориям и элементам ещё не накоплены" /> : null}
        </tbody>
      </DashboardTable>

      <DashboardTable title="Кампанейские ссылки" subtitle="Переходы по QR-кодам и deep-ссылкам за период">
        <thead><tr><th>Кампания</th><th>Источник</th><th>Размещение</th><th>Куда ведёт</th><th>Открытия</th><th>Уникальные</th></tr></thead>
        <tbody>
          {data.campaign_links.map((item) => (
            <tr key={item.campaign_link_id}><td data-label="Кампания"><strong>{item.campaign}</strong></td><td data-label="Источник">{item.source}</td><td data-label="Размещение">{item.placement}</td><td data-label="Куда ведёт">{item.target === "webapp" ? "Мини-приложение" : "Чат бота"}</td><td data-label="Открытия">{item.opens}</td><td data-label="Уникальные">{item.unique_opens}</td></tr>
          ))}
          {!data.campaign_links.length ? <EmptyRow columns={6} text="За период переходов по кампанейским ссылкам не было" /> : null}
        </tbody>
      </DashboardTable>

      <section className="dashboard-chart-grid">
        <DashboardTable title="Специальные возможности" subtitle="Открытия, запросы и подписки">
          <thead><tr><th>Возможность</th><th>Экран</th><th>Открытия</th><th>Запросы</th><th>Найдено</th><th>Подписки</th></tr></thead>
          <tbody>
            {data.capabilities.map((item) => (
              <tr key={`${item.capability_key}:${item.view_key}`}><td data-label="Возможность"><strong>{item.capability_key}</strong></td><td data-label="Экран">{item.view_key ?? "—"}</td><td data-label="Открытия">{item.opens}</td><td data-label="Запросы">{item.lookups}</td><td data-label="Найдено">{item.successful_lookups}</td><td data-label="Подписки">{item.subscription_changes}</td></tr>
            ))}
            {!data.capabilities.length ? <EmptyRow columns={6} text="Специальные возможности не использовались" /> : null}
          </tbody>
        </DashboardTable>
        <DashboardChart title={dashboardLabels.requestsShort} subtitle={`${current.ai_answers} вопросов закрыто автоответом за период`}>
          {data.tickets_trend.length ? <TicketTrendChart points={data.tickets_trend} /> : <DashboardEmpty>Обращений за период не было</DashboardEmpty>}
        </DashboardChart>
      </section>
    </div>
  );
}

function DashboardChart({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return <section className="card dashboard-panel"><div className="card-head"><div><h2 className="card-title">{title}</h2><p className="card-sub">{subtitle}</p></div></div><div className="card-body dashboard-chart-body">{children}</div></section>;
}

function DashboardTable({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return <section className="card dashboard-panel"><div className="card-head"><div><h2 className="card-title">{title}</h2><p className="card-sub">{subtitle}</p></div></div><div className="dashboard-table-wrap"><table className="dashboard-table">{children}</table></div></section>;
}

function EmptyRow({ columns, text }: { columns: number; text: string }) {
  return <tr><td colSpan={columns}><DashboardEmpty>{text}</DashboardEmpty></td></tr>;
}
