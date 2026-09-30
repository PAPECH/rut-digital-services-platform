import { useEffect, useState } from "react";

import type { BotRuntime } from "@/api/types";
import type { RuntimeCredentialPayload } from "@/features/bot-runtime/model/useBotRuntime";

export function BotCredentialForm({
  runtime,
  busy,
  onSave,
  onRotateRuntimeToken,
}: {
  runtime: BotRuntime | null;
  busy: boolean;
  onSave: (payload: RuntimeCredentialPayload) => Promise<unknown>;
  onRotateRuntimeToken: () => Promise<void>;
}) {
  const [source, setSource] = useState<"environment" | "managed">("managed");
  const [credentialEnvKey, setCredentialEnvKey] = useState("");
  const [botToken, setBotToken] = useState("");
  const [mode, setMode] = useState<BotRuntime["mode"]>("polling");

  useEffect(() => {
    if (!runtime) return;
    setSource(runtime.credential_source || "managed");
    setCredentialEnvKey(runtime.credential_env_key || "");
    setMode(runtime.mode);
  }, [runtime]);

  const managedTokenStored = runtime?.credential_source === "managed"
    && runtime.bot_token_configured;
  const tokenRequired = source === "managed" && !managedTokenStored;
  const saveDisabled = busy
    || (source === "environment" && !credentialEnvKey)
    || (tokenRequired && !botToken);

  return (
    <>
      <p className="muted">
        Токен уже сохранён и бот запущен. Меняйте эти настройки, только если нужен webhook
        вместо polling или переменная окружения вместо хранилища платформы.
      </p>
      <div className="bot-runtime-grid">
        <label>
          <span className="field-label">Хранение MAX-токена</span>
          <select className="select" value={source} onChange={(event) => setSource(event.target.value as typeof source)}>
            <option value="managed">Управляемое платформой</option>
            <option value="environment">Из ENV при деплое</option>
          </select>
        </label>
        {source === "environment" ? (
          <label>
            <span className="field-label">Переменная с MAX-токеном</span>
            <input className="input" placeholder="MAX_BOT_TOKEN_HR" value={credentialEnvKey} onChange={(event) => setCredentialEnvKey(event.target.value.toUpperCase())} />
          </label>
        ) : (
          <label>
            <span className="field-label">{tokenRequired ? "MAX-токен" : "Новый MAX-токен (необязательно)"}</span>
            <input
              className="input"
              type="password"
              autoComplete="new-password"
              placeholder={tokenRequired ? "Вставьте токен" : "Оставьте пустым, чтобы не менять"}
              value={botToken}
              onChange={(event) => setBotToken(event.target.value)}
            />
          </label>
        )}
        <label>
          <span className="field-label">Режим</span>
          <select className="select" value={mode} onChange={(event) => setMode(event.target.value as BotRuntime["mode"])}>
            <option value="polling">Polling</option>
            <option value="webhook">Webhook</option>
          </select>
        </label>
      </div>
      {source === "managed" ? (
        <p className="muted">
          Токен сохраняется в закрытом <code>bots.env</code> и не возвращается в админку.
          Runtime-токен{mode === "webhook" ? " и webhook secret" : ""} выпускаются автоматически.
        </p>
      ) : null}
      <div className="content-inline-actions">
        <button
          className="btn btn-secondary btn-sm"
          disabled={saveDisabled}
          onClick={() => void onSave({
            source,
            credential_env_key: source === "environment" ? credentialEnvKey : null,
            bot_token: source === "managed" && botToken ? botToken : null,
            mode,
          }).then(() => setBotToken("")).catch(() => undefined)}
        >
          {busy ? "Сохранение…" : "Сохранить подключение"}
        </button>
        {source === "environment" ? (
          <button className="btn btn-ghost btn-sm" disabled={busy} onClick={() => void onRotateRuntimeToken()}>
            {runtime?.token_configured ? "Перевыпустить runtime-токен" : "Выпустить runtime-токен"}
          </button>
        ) : null}
      </div>
    </>
  );
}
