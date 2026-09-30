import { useState } from "react";

import type { ConsentDocumentSave, ConsentDocumentSummary } from "@/entities/form-test/model/types";
import { formTestApi } from "@/features/form-test-management/api/formTestApi";
import * as styles from "./ConsentDocumentsPanel.css";

type EditingTarget = "new" | number;

export function ConsentDocumentsPanel({
  documents,
  loading,
  busy,
  error,
  onCreate,
  onUpdate,
  onDelete,
}: {
  documents: ConsentDocumentSummary[];
  loading: boolean;
  busy: boolean;
  error: string | null;
  onCreate: (payload: ConsentDocumentSave) => Promise<unknown>;
  onUpdate: (documentId: number, payload: ConsentDocumentSave) => Promise<boolean>;
  onDelete: (documentId: number) => Promise<boolean>;
}) {
  const [editing, setEditing] = useState<EditingTarget | null>(null);
  const [title, setTitle] = useState("");
  const [bodyHtml, setBodyHtml] = useState("");
  const [loadingDetail, setLoadingDetail] = useState(false);

  const startCreate = () => {
    setEditing("new");
    setTitle("");
    setBodyHtml("");
  };

  const startEdit = async (documentId: number) => {
    setEditing(documentId);
    setLoadingDetail(true);
    try {
      const detail = await formTestApi.getConsentDocument(documentId);
      setTitle(detail.title);
      setBodyHtml(detail.body_html);
    } finally {
      setLoadingDetail(false);
    }
  };

  const cancelEdit = () => setEditing(null);

  const save = async () => {
    if (editing === "new") {
      const created = await onCreate({ title, body_html: bodyHtml });
      if (created) setEditing(null);
    } else if (editing != null) {
      const ok = await onUpdate(editing, { title, body_html: bodyHtml });
      if (ok) setEditing(null);
    }
  };

  return (
    <div className="card">
      <div className="card-body">
        <div className={styles.header}>
          <h2 className={styles.title}>Документы согласия</h2>
          <button type="button" className="btn btn-primary btn-sm" onClick={startCreate} disabled={busy}>
            + Новый документ
          </button>
        </div>
        <p className={styles.hint}>
          Название и содержание документа, на который можно сослаться из галочки согласия перед
          отправкой теста (например, «Согласие на участие в исследовании»). Документы этого бота
          свободно создаются, редактируются и удаляются — удаление не меняет уже опубликованные
          версии тестов, которые на них ссылались.
        </p>
        {error && <div className={styles.errorBanner}>{error}</div>}

        {editing != null && (
          <div className={styles.editor}>
            <label className={styles.field}>
              <span>Название документа</span>
              <input
                className="input"
                value={title}
                disabled={loadingDetail}
                onChange={(event) => setTitle(event.target.value)}
              />
            </label>
            <label className={styles.field}>
              <span>Содержание (HTML)</span>
              <textarea
                className="input"
                rows={8}
                value={bodyHtml}
                disabled={loadingDetail}
                onChange={(event) => setBodyHtml(event.target.value)}
              />
            </label>
            <div className={styles.editorActions}>
              <button type="button" className="btn btn-ghost btn-sm" onClick={cancelEdit} disabled={busy}>
                Отмена
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => void save()}
                disabled={busy || loadingDetail || !title.trim() || !bodyHtml.trim()}
              >
                {busy ? "Сохранение…" : "Сохранить"}
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <p className={styles.hint}>Загрузка…</p>
        ) : documents.length === 0 ? (
          <p className={styles.hint}>Документов пока нет.</p>
        ) : (
          <ul className={styles.list}>
            {documents.map((document) => (
              <li key={document.id} className={styles.row}>
                <span className={styles.rowTitle}>{document.title}</span>
                <span className={styles.rowMeta}>
                  {document.updated_at ? new Date(document.updated_at).toLocaleString("ru-RU") : ""}
                </span>
                <div className={styles.rowActions}>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => void startEdit(document.id)}
                    disabled={busy}
                  >
                    Редактировать
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => {
                      if (window.confirm(`Удалить документ «${document.title}»?`)) {
                        void onDelete(document.id);
                      }
                    }}
                    disabled={busy}
                  >
                    Удалить
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
