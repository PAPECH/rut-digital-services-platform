import { useEffect, useState } from "react";
import { useI18n } from "@/i18n";
import { getConsentNotice } from "@/features/consent/api/consentApi";

function formatDate(value: string | null | undefined): string {
  if (!value) return "";
  try {
    return new Date(value).toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return value;
  }
}

// Fallback only -- used while the platform-admin-editable notice (GET /consent/notice/
// {lang}) is still loading, unset, or unreachable. Kept in sync in spirit with the
// migration's seed row, not literally the same string on purpose: an admin editing the
// live text shouldn't need to also touch mini-app source to change the fallback that only
// ever fires on an actual outage -- mirrors bot/app/main.py's _default_consent_notice.
// Plain text, no embedded link -- the policy document itself is always opened through the
// dedicated button below (onShowPolicy, always present and stable), not by parsing a link out
// of this admin-authored prose (that link isn't guaranteed to be there -- the real notice text
// today has none at all -- and briefly swapping from "has a link" to "doesn't" produced a
// visible flicker of the old inline-link-derived button).
function defaultNotice(lang: "ru" | "en"): string {
  if (lang === "en") {
    return "To use this bot, please confirm your consent to personal data processing.";
  }
  return (
    "Чтобы пользоваться ботом и мини-приложением, подтвердите согласие на обработку " +
    "персональных данных."
  );
}

interface ConsentGateScreenProps {
  // Present only for the "revoked, pending deletion" case -- absent for a brand-new /
  // never-consented identity, which is the more common path this screen covers.
  deletionDueAt?: string | null;
  busy: boolean;
  error?: string | null;
  onAccept: () => void;
  onShowPolicy: () => void;
}

// Same structural pattern as MaintenanceScreen (features/platform-manifest/ui/
// MaintenanceNotice.tsx) -- a full block, not a modal over broken content. Reuses its
// global CSS classes deliberately (see docs/tasks/064, "same visual/UX pattern").
export function ConsentGateScreen({
  deletionDueAt,
  busy,
  error,
  onAccept,
  onShowPolicy,
}: ConsentGateScreenProps) {
  const pending = Boolean(deletionDueAt);
  const { lang } = useI18n();
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    // Not fetched for the "pending deletion" state -- that screen shows the revoke
    // outcome, not the accept pitch, so there's nothing to load here for it.
    if (pending) return;
    void getConsentNotice(lang).then((value) => {
      if (active) setNotice(value);
    });
    return () => {
      active = false;
    };
  }, [lang, pending]);

  return (
    <main className="maintenance-screen">
      <div className="maintenance-screen__card">
        <div className="maintenance-screen__icon" aria-hidden="true">
          🔒
        </div>
        <h1>
          {pending
            ? "Согласие отозвано"
            : "Нужно подтвердить согласие на обработку персональных данных"}
        </h1>
        {pending ? (
          <p>
            Аккаунт и все данные (сообщения, заявки) будут удалены{" "}
            <b>{formatDate(deletionDueAt)}</b>, если согласие не будет подтверждено
            повторно.
          </p>
        ) : (
          <>
            <p
              className="policy-notice"
              dangerouslySetInnerHTML={{ __html: notice ?? defaultNotice(lang) }}
            />
            {
              // Same component/markup as content blocks (LinkBlockRenderer) -- opens the
              // policy as its own in-app screen (see App.tsx's showPolicy state), not an
              // external browser tab and not parsed out of the notice text above (which is
              // admin-authored prose that may or may not contain a link at all).
            }
            <button
              type="button"
              className="cms-link cms-link--card"
              style={{ marginTop: 12 }}
              onClick={onShowPolicy}
            >
              <span>
                {lang === "en"
                  ? "Personal Data Processing Regulation"
                  : "Положение о работе с персональными данными"}
              </span>
              <span aria-hidden="true">→</span>
            </button>
          </>
        )}
        {error ? (
          <p style={{ color: "var(--st-rej-fg, #b91c1c)" }}>{error}</p>
        ) : null}
        <button
          className="btn btn-primary"
          style={{ marginTop: 16 }}
          disabled={busy}
          onClick={onAccept}
        >
          {busy ? "Подтверждаем…" : "Я согласен(-на)"}
        </button>
      </div>
    </main>
  );
}
