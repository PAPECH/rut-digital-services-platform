import { useEffect, useState } from "react";
import { getPolicyDocument } from "@/features/consent/api/consentApi";

interface PolicyScreenProps {
  onBack: () => void;
}

// Full-screen, in-app -- not an external browser tab (see docs/tasks/066, "Superseded
// designs": MAX's own in-app "_blank" target didn't reliably render a plain document at all).
// Rendered as a local-state overlay from wherever it was opened (the consent gate, or the
// profile page) rather than a router route, so "Назад" always returns to exactly that screen.
export function PolicyScreen({ onBack }: PolicyScreenProps) {
  const [html, setHtml] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getPolicyDocument()
      .then((value) => {
        if (active) setHtml(value);
      })
      .catch((reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : "Не удалось загрузить документ");
      })
      .finally(() => {
        if (active) setLoaded(true);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="screen">
      <button type="button" className="btn btn-secondary" onClick={onBack} style={{ marginBottom: 16 }}>
        ← Назад
      </button>
      {!loaded ? <p className="muted">Загрузка…</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
      {loaded && !error ? (
        <div dangerouslySetInnerHTML={{ __html: html ?? "<p>Документ ещё не заполнен.</p>" }} />
      ) : null}
    </main>
  );
}
