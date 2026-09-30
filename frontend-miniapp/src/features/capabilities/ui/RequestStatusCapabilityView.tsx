import { useEffect, useMemo, useState } from "react";

import type {
  CapabilityViewProps,
  RequestStatusLookup,
  RequestStatusPublicConfig,
  RequestStatusSubscription,
} from "@/entities/capability/model/types";
import { capabilityApi } from "@/features/capabilities/api/capabilityApi";

function publicConfig(
  value: Record<string, unknown>,
): RequestStatusPublicConfig {
  return {
    title: String(value.title || "Проверить статус заявления"),
    subtitle: String(value.subtitle || "Введите номер заявления."),
    lookup_label: String(value.lookup_label || "Номер заявления"),
    not_found_text: String(value.not_found_text || "Заявление не найдено."),
    notifications_enabled: value.notifications_enabled !== false,
  };
}

export function RequestStatusCapabilityView({
  capability,
}: CapabilityViewProps) {
  const config = useMemo(
    () => publicConfig(capability.public_config),
    [capability.public_config],
  );
  const [number, setNumber] = useState("");
  const [result, setResult] = useState<RequestStatusLookup | null>(null);
  const [subscription, setSubscription] =
    useState<RequestStatusSubscription | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    capabilityApi.requestStatus
      .subscription()
      .then(setSubscription)
      .catch(() => undefined);
  }, []);

  const lookup = async () => {
    if (!number.trim()) return;
    setBusy("lookup");
    setError(null);
    try {
      setResult(await capabilityApi.requestStatus.lookup(number.trim()));
    } catch (reason) {
      setError((reason as Error).message || "Не удалось получить статус");
    } finally {
      setBusy(null);
    }
  };

  const toggleSubscription = async () => {
    const requestNumber =
      result?.request_number || subscription?.request_number;
    if (!requestNumber) return;
    const active = result?.is_subscribed ?? subscription?.is_active ?? false;
    setBusy("subscription");
    setError(null);
    try {
      const fresh = active
        ? await capabilityApi.requestStatus.unsubscribe(requestNumber)
        : await capabilityApi.requestStatus.subscribe(requestNumber);
      setSubscription(fresh);
      setResult((current) =>
        current ? { ...current, is_subscribed: fresh.is_active } : current,
      );
    } catch (reason) {
      setError((reason as Error).message || "Не удалось изменить подписку");
    } finally {
      setBusy(null);
    }
  };

  const subscribed = result?.is_subscribed ?? subscription?.is_active ?? false;
  return (
    <div className="capability-request-status">
      <header>
        <h1 className="screen-title">{config.title}</h1>
        <p className="screen-sub">{config.subtitle}</p>
      </header>
      <div className="card capability-request-status__form">
        <label className="field-label" htmlFor="request-status-number">
          {config.lookup_label}
        </label>
        <input
          id="request-status-number"
          className="input"
          value={number}
          maxLength={64}
          autoComplete="off"
          onChange={(event) => setNumber(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") void lookup();
          }}
        />
        <button
          type="button"
          className="btn btn-primary"
          disabled={!number.trim() || busy !== null}
          onClick={() => void lookup()}
        >
          {busy === "lookup" ? "Поиск…" : "Найти"}
        </button>
      </div>
      {error ? <div className="form-error">{error}</div> : null}
      {result ? (
        <section className="card capability-request-status__result">
          <span className="muted">Текущий статус</span>
          <strong>{result.status || config.not_found_text}</strong>
          {result.checked_at ? (
            <small className="muted">
              Актуально на {new Date(result.checked_at).toLocaleString("ru-RU")}
            </small>
          ) : null}
          {result.status && config.notifications_enabled ? (
            <button
              type="button"
              className="btn btn-secondary"
              disabled={busy !== null}
              onClick={() => void toggleSubscription()}
            >
              {busy === "subscription"
                ? "Сохранение…"
                : subscribed
                  ? "Отключить уведомления"
                  : "Уведомлять об изменениях"}
            </button>
          ) : null}
        </section>
      ) : subscription?.is_active ? (
        <section className="card capability-request-status__result">
          <span className="muted">Активная подписка</span>
          <strong>{subscription.request_number}</strong>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy !== null}
            onClick={() => void toggleSubscription()}
          >
            Отключить уведомления
          </button>
        </section>
      ) : null}
    </div>
  );
}
