import { useEffect, useState } from "react";

import { formTestApi } from "@/features/form-tests/api/formTestApi";

interface TestConsentDocumentScreenProps {
  testId: number;
  title: string;
  onBack: () => void;
}

// Full-screen, in-app overlay -- not an external browser tab, mirroring
// `features/consent/ui/PolicyScreen.tsx` for the same reason (docs/tasks/066): MAX's own in-app
// link target doesn't reliably render a plain document. Local-state overlay inside `TestPage`
// rather than a router route, so "Назад" always returns to the same in-progress attempt.
export function TestConsentDocumentScreen({ testId, title, onBack }: TestConsentDocumentScreenProps) {
  const [html, setHtml] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    formTestApi
      .getConsentDocument(testId)
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
  }, [testId]);

  return (
    <main className="screen">
      <button type="button" className="btn btn-secondary" onClick={onBack} style={{ marginBottom: 16 }}>
        ← Назад
      </button>
      <h1 className="screen-title">{title}</h1>
      {!loaded ? <p className="muted">Загрузка…</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
      {loaded && !error ? (
        <div dangerouslySetInnerHTML={{ __html: html ?? "<p>Документ ещё не заполнен.</p>" }} />
      ) : null}
    </main>
  );
}
