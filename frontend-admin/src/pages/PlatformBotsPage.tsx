import { useNavigate } from "react-router-dom";

import { BotInstanceCard } from "@/entities/bot-instance/ui/BotInstanceCard";
import { useBotSelection } from "@/features/bot-selection/model/BotSelectionContext";
import { useBotInstances } from "@/features/bot-instance-management/model/useBotInstances";
import { CreateBotForm } from "@/features/bot-instance-management/ui/CreateBotForm";
import { ConsentNoticePanel } from "@/features/consent-admin/ui/ConsentNoticePanel";
import { PolicyDocumentPanel } from "@/features/consent-admin/ui/PolicyDocumentPanel";
import { MaintenancePanel } from "@/features/maintenance/ui/MaintenancePanel";

export function PlatformBotsPage() {
  const navigate = useNavigate();
  const { selectBot } = useBotSelection();
  const {
    bots,
    loading,
    creating,
    error,
    includeDeleted,
    setIncludeDeleted,
    create,
    update,
    remove,
    restore,
  } = useBotInstances();

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">Боты платформы</h1>
          <p className="page-sub">
            Создание экземпляров и глобальное управление платформой.
          </p>
        </div>
      </div>

      <div className="platform-bots-layout">
        <div className="grid">
          <CreateBotForm creating={creating} onCreate={create} />
          <MaintenancePanel
            scope="global"
            title="Глобальный технический режим"
          />
          <ConsentNoticePanel />
          <PolicyDocumentPanel />
        </div>
        <section>
          <div className="bot-instance-grid__head">
            <h2 className="section-title">Экземпляры ({bots.length})</h2>
            <label className="staff-permission">
              <input
                type="checkbox"
                checked={includeDeleted}
                onChange={(event) => setIncludeDeleted(event.target.checked)}
              />
              <span>Показывать удалённых</span>
            </label>
          </div>
          {loading ? <p className="muted">Загрузка…</p> : null}
          {error ? <p className="form-error">{error}</p> : null}
          <div className="bot-instance-grid">
            {bots.map((bot) => (
              <BotInstanceCard
                key={bot.id}
                bot={bot}
                onUpdate={update}
                onDelete={remove}
                onRestore={restore}
                onOpen={(selectedBot) => {
                  selectBot(selectedBot.slug);
                  navigate("/dashboard");
                }}
              />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
