import { useCallback, useEffect, useState } from "react";
import { api } from "@/api/client";
import { Icon } from "@/components/Icon";

interface KbDoc {
  id: number;
  topic: string;
  content: string;
  tags: string[] | null;
  is_active: boolean;
  created_at: string;
  // Не-null для зеркал, автосозданных из FAQ (Task 052) — такие документы
  // редактируются/удаляются только через страницу FAQ, не отсюда.
  source_faq_id: number | null;
}

interface Draft {
  id: number | null;
  topic: string;
  content: string;
  tags: string;
  is_active: boolean;
}

interface KbTestMatchHit {
  document_id: number;
  topic: string;
  content: string;
  score: number;
}

interface KbTestMatchCandidate {
  document_id: number;
  topic: string;
  score: number;
}

interface KbTestMatchResult {
  tier: "auto" | "candidates" | "no_match" | "escalate" | "skip";
  hit: KbTestMatchHit | null;
  candidates: KbTestMatchCandidate[] | null;
  note: string | null;
}

const TIER_LABEL: Record<KbTestMatchResult["tier"], string> = {
  auto: "Авто-ответ",
  candidates: "Кандидаты",
  no_match: "Ничего не найдено",
  escalate: "Эскалация к сотруднику",
  skip: "Матчинг не выполнялся",
};

const emptyDraft: Draft = {
  id: null,
  topic: "",
  content: "",
  tags: "",
  is_active: true,
};

export function KbPage() {
  const [items, setItems] = useState<KbDoc[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [testQuery, setTestQuery] = useState("");
  const [testBusy, setTestBusy] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<KbTestMatchResult | null>(null);

  const reload = useCallback(() => {
    void api
      .get<KbDoc[]>("/kb/documents")
      .then(setItems)
      .catch(() => setItems([]));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const openCreate = () => setDraft({ ...emptyDraft });
  const openEdit = (d: KbDoc) =>
    setDraft({
      id: d.id,
      topic: d.topic,
      content: d.content,
      tags: (d.tags ?? []).join(", "),
      is_active: d.is_active,
    });

  const save = async () => {
    if (!draft) return;
    if (!draft.topic.trim() || !draft.content.trim()) {
      setError("Заполните тему и содержимое");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const tags = draft.tags
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const body = {
        topic: draft.topic.trim(),
        content: draft.content.trim(),
        tags: tags.length ? tags : null,
        is_active: draft.is_active,
      };
      if (draft.id == null) {
        await api.post("/kb/documents/one", body);
      } else {
        await api.patch(`/kb/documents/${draft.id}`, body);
      }
      setDraft(null);
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (d: KbDoc) => {
    if (!confirm(`Удалить документ «${d.topic}»?`)) return;
    await api.del(`/kb/documents/${d.id}`);
    reload();
  };

  const runTestMatch = async () => {
    const text = testQuery.trim();
    if (!text) return;
    setTestBusy(true);
    setTestError(null);
    try {
      const result = await api.post<KbTestMatchResult>("/kb/test-match", { text });
      setTestResult(result);
    } catch (e) {
      setTestError((e as Error).message);
      setTestResult(null);
    } finally {
      setTestBusy(false);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">База знаний</h1>
          <p className="page-sub">
            Бот подбирает документ по смыслу темы и ключевых слов — текст
            содержимого в поиске не участвует, поэтому формулируйте тему как
            вопрос пользователя, а синонимы и разговорные слова добавляйте в
            ключевые слова
          </p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>
          <span className="ico" style={{ width: 14, height: 14 }}>
            <Icon.Plus />
          </span>
          Добавить
        </button>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-head">
          <div>
            <h3 className="card-title">Тестовый режим</h3>
            <p className="card-sub">
              Проверьте, что реально ответит бот на вопрос — ничего не отправляется
              пользователю и не создаёт тикет.
            </p>
          </div>
        </div>
        <div className="card-body">
          <div style={{ display: "flex", gap: 8 }}>
            <input
              className="input"
              value={testQuery}
              onChange={(e) => setTestQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void runTestMatch();
                }
              }}
              placeholder="Например: когда будет готова справка"
              style={{ flex: 1 }}
            />
            <button
              className="btn btn-primary"
              disabled={testBusy || !testQuery.trim()}
              onClick={() => void runTestMatch()}
            >
              {testBusy ? "Проверяем…" : "Проверить"}
            </button>
          </div>
          {testError && (
            <p style={{ color: "var(--st-rej-fg)", fontSize: 13, marginTop: 10 }}>
              {testError}
            </p>
          )}
          {testResult && (
            <div style={{ marginTop: 14 }}>
              <span className="tag outline" style={{ fontSize: 12 }}>
                {TIER_LABEL[testResult.tier]}
              </span>
              {testResult.hit && (
                <div
                  style={{
                    marginTop: 10,
                    padding: "10px 14px",
                    border: "1px solid var(--line)",
                    borderRadius: 8,
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: 13 }}>
                    {testResult.hit.topic}{" "}
                    <span style={{ fontWeight: 400, color: "var(--ink-400)" }}>
                      · score {testResult.hit.score.toFixed(3)}
                    </span>
                  </div>
                  <div style={{ fontSize: 13, marginTop: 4, whiteSpace: "pre-wrap" }}>
                    {testResult.hit.content}
                  </div>
                </div>
              )}
              {testResult.candidates && testResult.candidates.length > 0 && (
                <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
                  {testResult.candidates.map((c) => (
                    <div
                      key={c.document_id}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        padding: "8px 12px",
                        border: "1px solid var(--line)",
                        borderRadius: 8,
                        fontSize: 13,
                      }}
                    >
                      <span>{c.topic}</span>
                      <span style={{ color: "var(--ink-400)" }}>score {c.score.toFixed(3)}</span>
                    </div>
                  ))}
                </div>
              )}
              {testResult.note && (
                <p style={{ fontSize: 13, color: "var(--ink-500)", marginTop: 10 }}>
                  {testResult.note}
                </p>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        {items.length === 0 ? (
          <div
            style={{
              padding: 32,
              textAlign: "center",
              color: "var(--ink-400)",
            }}
          >
            Документов нет
          </div>
        ) : (
          items.map((d) => (
            <div
              key={d.id}
              style={{
                display: "flex",
                gap: 12,
                alignItems: "flex-start",
                padding: "14px 18px",
                borderBottom: "1px solid var(--line)",
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 4,
                  }}
                >
                  <span style={{ fontWeight: 600, fontSize: 14 }}>
                    {d.topic}
                  </span>
                  {!d.is_active && <span className="tag neutral">скрыт</span>}
                  {d.source_faq_id != null && (
                    <span className="tag outline" style={{ fontSize: 11 }}>
                      из FAQ
                    </span>
                  )}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color: "var(--ink-500)",
                    whiteSpace: "pre-wrap",
                    maxHeight: 96,
                    overflow: "hidden",
                  }}
                >
                  {d.content}
                </div>
                {d.tags && d.tags.length > 0 && (
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 4,
                      marginTop: 6,
                    }}
                  >
                    {d.tags.map((t) => (
                      <span
                        key={t}
                        className="tag outline"
                        style={{ fontSize: 11 }}
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                {d.source_faq_id != null ? (
                  <span
                    style={{ fontSize: 12, color: "var(--ink-400)", whiteSpace: "nowrap" }}
                  >
                    редактируется на странице FAQ
                  </span>
                ) : (
                  <>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => openEdit(d)}
                    >
                      Изменить
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => void remove(d)}
                    >
                      Удалить
                    </button>
                  </>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {draft && (
        <KbDrawer
          draft={draft}
          setDraft={setDraft}
          onClose={() => setDraft(null)}
          onSave={save}
          busy={busy}
          error={error}
        />
      )}
    </div>
  );
}

function KbDrawer({
  draft,
  setDraft,
  onClose,
  onSave,
  busy,
  error,
}: {
  draft: Draft;
  setDraft: (d: Draft) => void;
  onClose: () => void;
  onSave: () => void | Promise<void>;
  busy: boolean;
  error: string | null;
}) {
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        display: "flex",
        justifyContent: "flex-end",
      }}
    >
      <div
        onClick={onClose}
        style={{
          position: "absolute",
          inset: 0,
          background: "rgba(11,23,41,.32)",
        }}
      />
      <div
        style={{
          position: "relative",
          width: 600,
          maxWidth: "100vw",
          height: "100%",
          background: "#fff",
          borderLeft: "1px solid var(--line)",
          boxShadow: "var(--shadow-lg)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            padding: "18px 22px",
            borderBottom: "1px solid var(--line)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h3 style={{ margin: 0, fontSize: 16 }}>
            {draft.id == null ? "Новый документ" : `Документ #${draft.id}`}
          </h3>
          <button className="btn btn-ghost btn-icon" onClick={onClose}>
            ×
          </button>
        </div>
        <div style={{ padding: 22, overflow: "auto", flex: 1 }}>
          <label className="field-label">Тема *</label>
          <input
            className="input"
            value={draft.topic}
            onChange={(e) => setDraft({ ...draft, topic: e.target.value })}
            placeholder="Например: «Срок изготовления справки»"
          />
          <label className="field-label" style={{ marginTop: 12 }}>
            Содержимое *
          </label>
          <textarea
            className="textarea"
            rows={10}
            value={draft.content}
            onChange={(e) => setDraft({ ...draft, content: e.target.value })}
            placeholder="Текст, который бот может процитировать в ответе пользователю."
          />
          <label className="field-label" style={{ marginTop: 12 }}>
            Ключевые слова и синонимы (через запятую)
          </label>
          <input
            className="input"
            value={draft.tags}
            onChange={(e) => setDraft({ ...draft, tags: e.target.value })}
            placeholder="справка, срок, готова, общага"
          />
          <div style={{ marginTop: 14 }}>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 13,
              }}
            >
              <input
                type="checkbox"
                checked={draft.is_active}
                onChange={(e) =>
                  setDraft({ ...draft, is_active: e.target.checked })
                }
              />
              Активен (учитывается AI-классификатором)
            </label>
          </div>
          <div>
            <label className="field-label">Предпросмотр</label>
            <div
              className="draft-preview"
              style={{
                border: "1px solid var(--line-strong)",
                borderRadius: 8,
                padding: "9px 12px",
                minHeight: 120,
                fontSize: 13,
                lineHeight: 1.5,
                background: "#fff",
                color: "var(--ink-900)",
                whiteSpace: "pre-wrap",
              }}
              dangerouslySetInnerHTML={{
                __html:
                  draft.content ??
                  "<span style='color:var(--ink-300)'>Предпросмотр появится здесь…</span>",
              }}
            />
          </div>
          {error && (
            <div
              style={{ marginTop: 12, color: "var(--st-rej-fg)", fontSize: 13 }}
            >
              {error}
            </div>
          )}
        </div>
        <div
          style={{
            padding: 16,
            borderTop: "1px solid var(--line)",
            display: "flex",
            gap: 8,
            justifyContent: "flex-end",
          }}
        >
          <button
            className="btn btn-secondary"
            onClick={onClose}
            disabled={busy}
          >
            Отмена
          </button>
          <button
            className="btn btn-primary"
            onClick={() => void onSave()}
            disabled={busy}
          >
            {busy ? "Сохраняем…" : "Сохранить"}
          </button>
        </div>
      </div>
    </div>
  );
}
