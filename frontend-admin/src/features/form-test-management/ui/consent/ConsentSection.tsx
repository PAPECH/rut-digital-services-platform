import { useRef } from "react";
import type { ReactNode } from "react";

import type { ConsentDocumentSummary, TestDraft } from "@/entities/form-test/model/types";
import {
  CONSENT_DOCUMENT_LINK_PLACEHOLDER,
  consentCheckboxTextHasLink,
  splitConsentCheckboxText,
} from "@/features/form-test-management/lib/consentPlaceholder";
import * as styles from "./ConsentSection.css";

function renderPreview(text: string, documentTitle: string): ReactNode {
  const parts = splitConsentCheckboxText(text);
  return parts.map((part, index) => (
    <span key={index}>
      {part}
      {index < parts.length - 1 && <span className={styles.previewLink}>{documentTitle}</span>}
    </span>
  ));
}

export function ConsentSection({
  draft,
  documents,
  onChange,
}: {
  draft: TestDraft;
  documents: ConsentDocumentSummary[];
  onChange: (patch: Partial<TestDraft>) => void;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const checkboxText = draft.consent_checkbox_text ?? "";
  const hasLink = consentCheckboxTextHasLink(checkboxText);
  const selectedDocument = documents.find((document) => document.id === draft.consent_document_id) ?? null;

  const insertLink = () => {
    const el = textareaRef.current;
    const start = el?.selectionStart ?? checkboxText.length;
    const end = el?.selectionEnd ?? checkboxText.length;
    const next = checkboxText.slice(0, start) + CONSENT_DOCUMENT_LINK_PLACEHOLDER + checkboxText.slice(end);
    onChange({ consent_checkbox_text: next });
    requestAnimationFrame(() => {
      const cursor = start + CONSENT_DOCUMENT_LINK_PLACEHOLDER.length;
      el?.focus();
      el?.setSelectionRange(cursor, cursor);
    });
  };

  return (
    <div>
      <h3>Согласие на участие</h3>
      <label className={styles.toggle}>
        <input
          type="checkbox"
          checked={draft.consent_enabled}
          onChange={(event) => onChange({ consent_enabled: event.target.checked })}
        />
        <span>Требовать согласие перед отправкой теста</span>
      </label>

      {draft.consent_enabled && (
        <div className={styles.body}>
          <label className={styles.field}>
            <span>Документ</span>
            <select
              className="input"
              value={draft.consent_document_id ?? ""}
              onChange={(event) =>
                onChange({ consent_document_id: event.target.value ? Number(event.target.value) : null })
              }
            >
              <option value="">— выберите документ —</option>
              {documents.map((document) => (
                <option key={document.id} value={document.id}>
                  {document.title}
                </option>
              ))}
            </select>
          </label>
          {draft.consent_document_missing && (
            <p className={styles.warning}>
              Выбранный документ был удалён. Выберите другой документ на вкладке «Документы» или
              отключите согласие — иначе публикация не пройдёт.
            </p>
          )}

          <label className={styles.field}>
            <span>Текст галочки под кнопкой отправки</span>
            <span className={styles.hint}>
              Нажмите на кнопку ниже, чтобы вставить ссылку на документ — не нужно запоминать
              синтаксис плейсхолдера.
            </span>
          </label>
          <div>
            <button type="button" className="btn btn-ghost btn-sm" onClick={insertLink}>
              + Вставить ссылку на документ
            </button>
          </div>
          <textarea
            ref={textareaRef}
            className="input"
            rows={3}
            value={checkboxText}
            onChange={(event) => onChange({ consent_checkbox_text: event.target.value })}
            placeholder="Например: Я согласен на участие в исследовании. Подробнее — (вставьте ссылку кнопкой выше)"
          />
          {!hasLink && checkboxText.trim().length > 0 && (
            <p className={styles.warning}>
              Текст не содержит ссылку на документ — добавьте её кнопкой выше, иначе публикация не
              пройдёт.
            </p>
          )}

          {checkboxText.trim().length > 0 && (
            <div className={styles.preview}>
              <span className={styles.previewLabel}>Предпросмотр:</span>
              <label className={styles.previewCheckbox}>
                <input type="checkbox" disabled />
                <span>{renderPreview(checkboxText, selectedDocument?.title ?? "документ")}</span>
              </label>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
