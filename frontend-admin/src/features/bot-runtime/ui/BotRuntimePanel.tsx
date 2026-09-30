import { useState } from "react";

import type { BotRuntime } from "@/api/types";
import { useBotRuntime } from "@/features/bot-runtime/model/useBotRuntime";
import { BotCredentialForm } from "@/features/bot-runtime/ui/BotCredentialForm";
import { BotRuntimeDetails } from "@/features/bot-runtime/ui/BotRuntimeDetails";

const statusLabels: Record<BotRuntime["status"], string> = {
  online: "Подключён",
  offline: "Не в сети",
  error: "Ошибка",
  not_connected: "Запускается…",
};

export function BotRuntimePanel({ botId, botSlug }: { botId: number; botSlug: string }) {
  const state = useBotRuntime(botId);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [newToken, setNewToken] = useState("");
  const [tokenError, setTokenError] = useState<string | null>(null);

  return (
    <section className="bot-runtime-panel">
      <div className="bot-runtime-panel__head">
        <strong>Подключение процесса</strong>
        {state.runtime ? (
          <span className={`tag ${state.runtime.status === "online" ? "done" : "neutral"}`}>
            {statusLabels[state.runtime.status]}
          </span>
        ) : null}
      </div>
      <BotRuntimeDetails
        runtime={state.runtime}
        botSlug={botSlug}
        issuedToken={state.issuedToken}
        error={state.error}
      />
      <div>
        <span className="field-label">Заменить токен MAX-бота</span>
        <div className="content-inline-actions">
          <input
            className="input"
            type="password"
            autoComplete="new-password"
            placeholder="Оставьте пустым, чтобы не менять"
            value={newToken}
            onChange={(event) => setNewToken(event.target.value)}
          />
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={newToken.trim().length < 16 || state.busy}
            onClick={() => {
              setTokenError(null);
              void state
                .configure({
                  source: "managed",
                  credential_env_key: null,
                  bot_token: newToken,
                  mode: state.runtime?.mode ?? "polling",
                })
                .then(() => setNewToken(""))
                .catch((reason) => setTokenError((reason as Error).message));
            }}
          >
            {state.busy ? "Сохранение…" : "Обновить токен"}
          </button>
        </div>
        {tokenError ? <p className="form-error">{tokenError}</p> : null}
      </div>
      <button
        type="button"
        className="btn btn-ghost btn-sm bot-runtime-advanced-toggle"
        onClick={() => setAdvancedOpen((open) => !open)}
      >
        {advancedOpen ? "Скрыть расширенные настройки" : "Расширенные настройки"}
      </button>
      {advancedOpen ? (
        <BotCredentialForm
          runtime={state.runtime}
          busy={state.busy}
          onSave={state.configure}
          onRotateRuntimeToken={state.rotateRuntimeToken}
        />
      ) : null}
    </section>
  );
}
