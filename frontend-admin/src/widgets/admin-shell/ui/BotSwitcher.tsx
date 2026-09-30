import { useBotSelection } from "@/features/bot-selection/model/BotSelectionContext";

export function BotSwitcher() {
  const { bots, selectedSlug, loading, error, selectBot } = useBotSelection();

  if (!bots.length && !loading) return null;

  return (
    <label className="bot-switcher">
      <span>Бот</span>
      <select
        value={selectedSlug}
        disabled={loading || Boolean(error)}
        title={error || undefined}
        onChange={(event) => selectBot(event.target.value)}
      >
        {loading && !bots.length ? <option>Загрузка…</option> : null}
        {bots.map((bot) => (
          <option key={bot.id} value={bot.slug}>
            {bot.name}
          </option>
        ))}
      </select>
    </label>
  );
}
