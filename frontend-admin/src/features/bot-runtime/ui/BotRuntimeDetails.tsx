import type { BotRuntime } from "@/api/types";
import {
  runtimeTokenEnvKey,
  webhookSecretEnvKey,
} from "@/features/bot-runtime/model/runtimeEnvKeys";

export function BotRuntimeDetails({
  runtime,
  botSlug,
  issuedToken,
  error,
}: {
  runtime: BotRuntime | null;
  botSlug: string;
  issuedToken: string | null;
  error: string | null;
}) {
  if (!runtime && !error) return null;
  const environment = runtime?.credential_source === "environment";
  return (
    <div className="bot-runtime-details">
      {runtime?.last_seen_at ? (
        <p className="muted">
          Последний heartbeat: {new Date(runtime.last_seen_at).toLocaleString("ru-RU")}
          {runtime.runtime_version ? ` · ${runtime.runtime_version}` : ""}
        </p>
      ) : null}
      {runtime?.username || runtime?.max_bot_id ? (
        <div className="bot-runtime-identity">
          <div className="bot-runtime-identity__avatar" aria-hidden="true">
            {(runtime.username || "MAX").replace(/^@/, "").slice(0, 1).toUpperCase()}
          </div>
          <div className="bot-runtime-identity__body">
            <span>Подключённый MAX-бот</span>
            <strong>
              {runtime.username ? `@${runtime.username.replace(/^@/, "")}` : "Username не получен"}
            </strong>
            {runtime.max_bot_id ? <code>MAX ID: {runtime.max_bot_id}</code> : null}
          </div>
          <span className={`tag ${runtime.status === "online" ? "done" : "neutral"}`}>
            {runtime.status === "online" ? "Подтверждён" : "Был подключён"}
          </span>
        </div>
      ) : runtime?.bot_token_configured ? (
        <div className="bot-runtime-identity bot-runtime-identity--pending">
          <div className="bot-runtime-identity__avatar" aria-hidden="true">?</div>
          <div className="bot-runtime-identity__body">
            <span>MAX-бот определяется</span>
            <strong>Запустите процесс подключения</strong>
            <small>Username и MAX ID появятся автоматически после первого heartbeat.</small>
          </div>
        </div>
      ) : null}
      {runtime?.last_error_code ? <p className="form-error">Ошибка процесса: {runtime.last_error_code}</p> : null}
      {runtime?.token_configured && environment ? (
        <p className="muted">Runtime-токен должен находиться в <code>{runtimeTokenEnvKey(botSlug)}</code>.</p>
      ) : null}
      {runtime?.mode === "webhook" && environment ? (
        <p className="muted">
          Webhook secret: <code>{webhookSecretEnvKey(botSlug)}</code>, URL: <code>/webhook/{botSlug}</code>.
        </p>
      ) : null}
      {issuedToken ? (
        <div className="bot-runtime-secret">
          <strong>Скопируйте сейчас: повторно токен не показывается.</strong>
          <code>{issuedToken}</code>
          <button className="btn btn-ghost btn-sm" onClick={() => void navigator.clipboard.writeText(issuedToken)}>Копировать</button>
        </div>
      ) : null}
      {error ? <p className="form-error">{error}</p> : null}
    </div>
  );
}
