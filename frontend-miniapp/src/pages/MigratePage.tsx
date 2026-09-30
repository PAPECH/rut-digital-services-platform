import React from "react";
import { openMaxLink } from "@/max/bridge";
export interface BotMigrationNoticeProps {
  /** Название старого бота (тот, что теперь неактуален) */
  oldBotName?: string;
  /** Название нового, актуального бота */
  newBotName?: string;
  /** Ссылка на нового бота в MAX (deep link) */
  newBotUrl?: string;
  /** Обработчик клика по основной кнопке (если нужен кастомный переход вместо ссылки) */
  onOpenNewBot?: () => void;
  /** Обработчик клика "Понятно" / закрытия экрана */
  onDismiss?: () => void;
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    minHeight: "100%",
    padding: "32px 24px",
    boxSizing: "border-box",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  iconWrap: {
    width: 72,
    height: 72,
    borderRadius: "50%",
    background: "#EEF2FF",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 24,
  },
  title: {
    fontSize: 20,
    fontWeight: 600,
    color: "#1A1A1A",
    margin: "0 0 12px",
    lineHeight: 1.3,
  },
  description: {
    fontSize: 15,
    fontWeight: 400,
    color: "#6B7280",
    lineHeight: 1.5,
    margin: "0 0 8px",
    maxWidth: 320,
  },
  botNameHighlight: {
    color: "#1A1A1A",
    fontWeight: 600,
  },
  actions: {
    width: "100%",
    maxWidth: 320,
    marginTop: 24,
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  primaryButton: {
    width: "100%",
    padding: "14px 20px",
    borderRadius: 12,
    border: "none",
    background: "var(--brand)",
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: 600,
    cursor: "pointer",
    textDecoration: "none",
    display: "inline-block",
    boxSizing: "border-box",
  },
  secondaryButton: {
    width: "100%",
    padding: "14px 20px",
    borderRadius: 12,
    border: "none",
    background: "transparent",
    color: "#6B7280",
    fontSize: 15,
    fontWeight: 500,
    cursor: "pointer",
  },
};
export const BotMigrationNotice: React.FC<BotMigrationNoticeProps> = ({
  oldBotName = "этого бота",
  newBotName = "Помощник кРУТя",
  newBotUrl = "https://max.ru/rut_miit_bot?start=migrate",
  onOpenNewBot = () => openMaxLink(newBotUrl),
  onDismiss,
}) => {
  const handlePrimaryClick = (e: React.MouseEvent) => {
    if (onOpenNewBot) {
      e.preventDefault();
      onOpenNewBot();
    }
  };

  return (
    <div style={styles.wrapper}>
      <h1 style={styles.title}>Бот переехал</h1>

      <p style={styles.description}>
        Функциональность {oldBotName} перенесена в другого бота в MAX —{" "}
        <span style={styles.botNameHighlight}>{newBotName}</span>. Там доступна
        вся актуальная информация по поступлению, навигатор первокурсника и
        сервисы МФЦ.
      </p>

      <div style={styles.actions}>
        <a
          href={newBotUrl || "#"}
          onClick={handlePrimaryClick}
          style={styles.primaryButton}
        >
          Перейти в {newBotName}
        </a>
        {onDismiss && (
          <button style={styles.secondaryButton} onClick={onDismiss}>
            Понятно
          </button>
        )}
      </div>
    </div>
  );
};

export default BotMigrationNotice;
