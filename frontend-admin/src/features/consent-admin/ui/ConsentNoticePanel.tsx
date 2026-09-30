import { useEffect, useState } from "react";
import { api } from "@/api/client";

interface ConsentNoticeOut {
  key: string;
  value: string | null;
}

const LANGS = ["ru", "en"] as const;

// Platform-wide (not per-bot) -- consent, like this prompt, is the same across every bot
// (Task 064). Mirrors BotSettingsPage.tsx's bot_start_message_* editor 1:1, just pointed
// at /consent/admin/notice instead of the per-bot /settings/{key}.
export function ConsentNoticePanel() {
  const [values, setValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    void api
      .get<ConsentNoticeOut[]>("/consent/admin/notice")
      .then((rows) => {
        const v: Record<string, string> = {};
        for (const r of rows) v[r.key] = r.value ?? "";
        setValues(v);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Не удалось загрузить текст");
      })
      .finally(() => setLoading(false));
  }, []);

  const save = async (lang: string) => {
    setSaving(lang);
    setError(null);
    try {
      await api.put(`/consent/admin/notice/${lang}`, { value: values[lang] ?? "" });
      setSavedAt(new Date().toLocaleTimeString());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Не удалось сохранить текст");
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h3 className="card-title">Плашка согласия на обработку персональных данных</h3>
          <p className="card-sub">
            Показывается снизу стартового сообщения бота, пока человек не подтвердил
            согласие — вставьте сюда ссылку на актуальное положение (поддерживается HTML,
            например {'<a href="...">текст</a>'}).
          </p>
        </div>
      </div>
      <div className="card-body">
        {loading ? <p className="muted">Загрузка…</p> : null}
        {error ? <p className="form-error">{error}</p> : null}
        {LANGS.map((lang) => (
          <div key={lang} style={{ marginBottom: 16 }}>
            <label className="lbl" style={{ display: "block", marginBottom: 6 }}>
              {lang === "ru" ? "Текст (RU)" : "Text (EN)"}
            </label>
            <textarea
              className="textarea"
              style={{ minHeight: 120, resize: "vertical" }}
              value={values[lang] ?? ""}
              onChange={(e) => setValues((prev) => ({ ...prev, [lang]: e.target.value }))}
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
                {savedAt ? `Сохранено в ${savedAt}` : "Изменения применятся к следующему /start"}
              </span>
              <button
                className="btn btn-primary"
                disabled={saving === lang}
                onClick={() => void save(lang)}
              >
                {saving === lang ? "Сохранение…" : "Сохранить"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
