import { useEffect, useState } from "react";
import { api } from "@/api/client";

interface PolicyDocumentOut {
  value: string;
}

// Platform-wide (not per-bot), same scope as ConsentNoticePanel right next to it on
// PlatformBotsPage.tsx. The policy document is admin-authored HTML rendered on our own page
// (GET /consent/policy-document) -- not an external URL or an uploaded file (both tried and
// dropped in the same session: an uploaded file needs a correct Content-Type to open
// reliably, and MAX's own in-app "_blank" target didn't reliably provide one, producing a
// blank screen). Mirrors ConsentNoticePanel.tsx's editor 1:1, just one field instead of
// per-language ones.
export function PolicyDocumentPanel() {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    void api
      .get<PolicyDocumentOut>("/consent/admin/policy-document")
      .then((doc) => setValue(doc.value))
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Не удалось загрузить документ");
      })
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      await api.put<PolicyDocumentOut>("/consent/admin/policy-document", { value });
      setSavedAt(new Date().toLocaleTimeString());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось сохранить документ");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3 className="card-title">Документ политики обработки персональных данных</h3>
          <p className="card-sub">
            Полный текст документа (поддерживается HTML) — открывается по отдельной ссылке
            из плашки согласия и из бота, на нашей собственной странице.
          </p>
        </div>
      </div>
      <div className="card-body">
        {loading ? <p className="muted">Загрузка…</p> : null}
        {error ? <p className="form-error">{error}</p> : null}
        <textarea
          className="textarea"
          style={{ minHeight: 240, resize: "vertical" }}
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <div
          style={{
            marginTop: 8,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: 12, color: "var(--ink-400)" }}>
            {savedAt ? `Сохранено в ${savedAt}` : ""}
          </span>
          <button className="btn btn-primary" disabled={saving} onClick={() => void save()}>
            {saving ? "Сохранение…" : "Сохранить"}
          </button>
        </div>
      </div>
    </div>
  );
}
