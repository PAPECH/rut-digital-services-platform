import { useEffect, useMemo, useState } from "react";

import type {
  AdmissionRatingLookup,
  AdmissionRatingPublicConfig,
  AdmissionRatingSubscription,
  CapabilityViewProps,
} from "@/entities/capability/model/types";
import { capabilityApi } from "@/features/capabilities/api/capabilityApi";

function publicConfig(value: Record<string, unknown>): AdmissionRatingPublicConfig {
  return {
    admission_year: Number(value.admission_year || new Date().getFullYear()),
    title: String(value.title || "Место в рейтинге"),
    subtitle: String(value.subtitle || "Введите уникальный код поступающего."),
    lookup_label: String(value.lookup_label || "Уникальный код поступающего"),
    not_found_text: String(value.not_found_text || "Записи в рейтинге не найдены."),
    notifications_enabled: value.notifications_enabled !== false,
  };
}

export function AdmissionRatingCapabilityView({ capability }: CapabilityViewProps) {
  const config = useMemo(() => publicConfig(capability.public_config), [capability.public_config]);
  const [code, setCode] = useState("");
  const [result, setResult] = useState<AdmissionRatingLookup | null>(null);
  const [subscription, setSubscription] = useState<AdmissionRatingSubscription | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    capabilityApi.admissionRating.subscription().then(setSubscription).catch(() => undefined);
  }, []);

  const lookup = async () => {
    if (!code.trim()) return;
    setBusy("lookup");
    setError(null);
    try {
      setResult(await capabilityApi.admissionRating.lookup(code.trim()));
    } catch (reason) {
      setError((reason as Error).message || "Не удалось получить рейтинг");
    } finally {
      setBusy(null);
    }
  };

  const toggleSubscription = async () => {
    const applicantCode = result?.applicant_code || subscription?.applicant_code;
    if (!applicantCode) return;
    const active = result?.is_subscribed ?? subscription?.is_active ?? false;
    setBusy("subscription");
    setError(null);
    try {
      const fresh = active
        ? await capabilityApi.admissionRating.unsubscribe(applicantCode)
        : await capabilityApi.admissionRating.subscribe(applicantCode);
      setSubscription(fresh);
      setResult((current) => current ? { ...current, is_subscribed: fresh.is_active } : current);
    } catch (reason) {
      setError((reason as Error).message || "Не удалось изменить подписку");
    } finally {
      setBusy(null);
    }
  };

  const subscribed = result?.is_subscribed ?? subscription?.is_active ?? false;
  return (
    <div className="capability-admission-rating">
      <header>
        <h1 className="screen-title">{config.title}</h1>
        <p className="screen-sub">{config.subtitle}</p>
      </header>
      <div className="card capability-request-status__form">
        <label className="field-label" htmlFor="admission-rating-code">{config.lookup_label}</label>
        <input id="admission-rating-code" className="input" value={code} maxLength={64}
          autoComplete="off" onChange={(event) => setCode(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter") void lookup(); }} />
        <button type="button" className="btn btn-primary" disabled={!code.trim() || busy !== null}
          onClick={() => void lookup()}>{busy === "lookup" ? "Поиск…" : "Найти"}</button>
      </div>
      {error ? <div className="form-error">{error}</div> : null}
      {result ? (
        <section className="capability-rating-results">
          {result.entries.length ? result.entries.map((entry) => (
            <article className="rating-card" key={`${entry.plan_id}:${entry.competition}`}>
              <div className="rating-card__head"><span className="rating-card__code">{entry.qualification}</span>
                <span className="rating-card__spec">{entry.specialty}</span></div>
              <div className="rating-card__competition">{entry.competition}</div>
              <div className="rating-card__group">{entry.group_name}</div>
              <div className="rating-card__stat-row">
                <div className="rating-card__rank"><span className="rating-card__rank-current">{entry.position}</span>
                  <span className="rating-card__rank-total">из {entry.total}</span></div>
                <div className="rating-card__points">Балл: {entry.points}</div>
              </div>
              <div className="rating-card__footer">Приоритет: {entry.preference}</div>
            </article>
          )) : <div className="card content-empty-state">{config.not_found_text}</div>}
          {result.entries.length && config.notifications_enabled ? (
            <button type="button" className="btn btn-secondary" disabled={busy !== null}
              onClick={() => void toggleSubscription()}>
              {busy === "subscription" ? "Сохранение…" : subscribed ? "Отключить уведомления" : "Уведомлять об изменениях"}
            </button>
          ) : null}
        </section>
      ) : subscription?.is_active ? (
        <section className="card capability-request-status__result">
          <span className="muted">Активная подписка</span><strong>{subscription.applicant_code}</strong>
          <button type="button" className="btn btn-secondary" disabled={busy !== null}
            onClick={() => void toggleSubscription()}>Отключить уведомления</button>
        </section>
      ) : null}
    </div>
  );
}
