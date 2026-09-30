import { useCallback, useEffect, useState } from "react";
import { api } from "@/api/client";
import { Icon } from "@/components/Icon";

interface FaqItem {
  id: number;
  question: string;
  answer: string;
  is_active: boolean;
  order: number;
}

interface Draft {
  id: number | null;
  question: string;
  answer: string;
  is_active: boolean;
  order: number;
}

const emptyDraft: Draft = {
  id: null,
  question: "",
  answer: "",
  is_active: true,
  order: 0,
};

export function FaqPage() {
  const [items, setItems] = useState<FaqItem[]>([]);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    void api
      .get<FaqItem[]>("/faq")
      .then(setItems)
      .catch(() => setItems([]));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const openCreate = () => setDraft({ ...emptyDraft });
  const openEdit = (f: FaqItem) =>
    setDraft({
      id: f.id,
      question: f.question,
      answer: f.answer,
      is_active: f.is_active,
      order: f.order,
    });

  const save = async () => {
    if (!draft) return;
    if (!draft.question.trim() || !draft.answer.trim()) {
      setError("Заполните вопрос и ответ");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const body = {
        question: draft.question.trim(),
        answer: draft.answer.trim(),
        is_active: draft.is_active,
        order: draft.order,
      };
      if (draft.id == null) {
        await api.post("/faq", body);
      } else {
        await api.patch(`/faq/${draft.id}`, body);
      }
      setDraft(null);
      reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (f: FaqItem) => {
    if (!confirm(`Удалить FAQ «${f.question.slice(0, 50)}»?`)) return;
    await api.del(`/faq/${f.id}`);
    reload();
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1 className="page-title">FAQ</h1>
          <p className="page-sub">
            Часто задаваемые вопросы, которые видит студент в mini-app
          </p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>
          <span className="ico" style={{ width: 14, height: 14 }}>
            <Icon.Plus />
          </span>
          Добавить
        </button>
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
            FAQ пока не добавлены
          </div>
        ) : (
          items.map((f) => (
            <div
              key={f.id}
              style={{
                display: "flex",
                gap: 12,
                alignItems: "flex-start",
                padding: "14px 18px",
                borderBottom: "1px solid var(--line)",
              }}
            >
              <div style={{ flex: 1 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    marginBottom: 4,
                  }}
                >
                  <span style={{ fontWeight: 600, fontSize: 14 }}>
                    {f.question}
                  </span>
                  {!f.is_active && <span className="tag neutral">скрыт</span>}
                  <span className="tag outline" style={{ fontSize: 11 }}>
                    №{f.order}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: 13,
                    color: "var(--ink-500)",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {f.answer}
                </div>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={() => openEdit(f)}
                >
                  Изменить
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => void remove(f)}
                >
                  Удалить
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {draft && (
        <FaqDrawer
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

function FaqDrawer({
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
          width: 560,
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
            {draft.id == null ? "Новый FAQ" : `FAQ #${draft.id}`}
          </h3>
          <button className="btn btn-ghost btn-icon" onClick={onClose}>
            ×
          </button>
        </div>
        <div style={{ padding: 22, overflow: "auto", flex: 1 }}>
          <label className="field-label">Вопрос *</label>
          <input
            className="input"
            value={draft.question}
            onChange={(e) => setDraft({ ...draft, question: e.target.value })}
          />
          <label className="field-label" style={{ marginTop: 12 }}>
            Ответ *
          </label>
          <textarea
            className="textarea"
            rows={5}
            value={draft.answer}
            onChange={(e) => setDraft({ ...draft, answer: e.target.value })}
          />
          <div
            style={{
              display: "flex",
              gap: 16,
              marginTop: 14,
              alignItems: "center",
            }}
          >
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
              Активен
            </label>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 13,
              }}
            >
              Порядок
              <input
                className="input"
                type="number"
                style={{ width: 80 }}
                value={draft.order}
                onChange={(e) =>
                  setDraft({ ...draft, order: Number(e.target.value) || 0 })
                }
              />
            </label>
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
