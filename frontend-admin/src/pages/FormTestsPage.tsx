import { useState } from "react";

import { EntityDropdownPicker } from "@/components/EntityDropdownPicker";
import { ConsentDocumentsPanel } from "@/features/form-test-management/ui/consent/ConsentDocumentsPanel";
import { CreateTestForm } from "@/features/form-test-management/ui/CreateTestForm";
import { FormTestOverview } from "@/features/form-test-management/ui/FormTestOverview";
import { TestDraftEditor } from "@/features/form-test-management/ui/TestDraftEditor";
import { TestResultsSection } from "@/features/form-test-management/ui/TestResultsSection";
import { useConsentDocuments } from "@/features/form-test-management/model/useConsentDocuments";
import { useFormTests } from "@/features/form-test-management/model/useFormTests";
import { useTestAttempts } from "@/features/form-test-management/model/useTestAttempts";
import { useTestDraftBuilder } from "@/features/form-test-management/model/useTestDraftBuilder";
import * as styles from "./FormTestsPage.css";

type Tab = "overview" | "results" | "builder" | "documents";

const TAB_LABELS: Record<Tab, string> = {
  overview: "Обзор",
  results: "Результаты",
  builder: "Редактировать",
  documents: "Документы",
};

export function FormTestsPage() {
  const { tests, active, detail, busy, error, selectTest, toggle, create, move, reload } =
    useFormTests();
  const {
    attempts,
    statusFilter,
    setStatusFilter,
    loading: attemptsLoading,
  } = useTestAttempts(active?.id ?? null);
  const builder = useTestDraftBuilder(active?.id ?? null, reload);
  const consentDocuments = useConsentDocuments();
  const [creating, setCreating] = useState(false);
  const [tab, setTab] = useState<Tab>("overview");

  return (
    <div className="page">
      <div className={styles.pageHead}>
        <h1 className="page-title">Тесты</h1>
        <button type="button" className="btn btn-primary" onClick={() => setCreating(true)}>
          Добавить тест
        </button>
      </div>
      {error && <div className={styles.errorBanner}>{error}</div>}
      {creating && (
        <CreateTestForm
          order={tests.length}
          onCreate={create}
          onCancel={() => setCreating(false)}
        />
      )}
      <div className={styles.main}>
        <div className={styles.pickerTabsRow}>
          <EntityDropdownPicker
            items={tests.map((test) => ({
              id: test.id,
              title: test.name,
              subtitle: test.slug,
              badge: test.is_archived ? { text: "архив", tone: "neutral" } : undefined,
            }))}
            activeId={active?.id ?? null}
            reordering={busy}
            placeholder="Выберите тест"
            emptyLabel="Тестов пока нет"
            onSelect={selectTest}
            onMove={move}
          />
          <div className={styles.tabs} role="tablist" aria-label="Раздел теста">
            {(["overview", "results", "builder", "documents"] as Tab[]).map((item) => (
              <button
                key={item}
                type="button"
                role="tab"
                aria-selected={tab === item}
                className={tab === item ? styles.tabActive : styles.tab}
                disabled={item !== "documents" && !active}
                onClick={() => setTab(item)}
              >
                {TAB_LABELS[item]}
              </button>
            ))}
          </div>
        </div>

        {tab === "documents" ? (
          <ConsentDocumentsPanel
            documents={consentDocuments.documents}
            loading={consentDocuments.loading}
            busy={consentDocuments.busy}
            error={consentDocuments.error}
            onCreate={consentDocuments.create}
            onUpdate={consentDocuments.update}
            onDelete={consentDocuments.remove}
          />
        ) : tab === "results" && active && detail ? (
          <TestResultsSection
            testId={active.id}
            detail={detail}
            attempts={attempts}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            loading={attemptsLoading}
          />
        ) : tab === "overview" || !active ? (
          <FormTestOverview
            detail={detail}
            busy={busy}
            onToggle={(payload) => {
              if (active) void toggle(active.id, payload);
            }}
          />
        ) : builder.draft ? (
          <TestDraftEditor
            testId={active.id}
            draft={builder.draft}
            onChange={builder.setDraft}
            busy={builder.busy}
            error={builder.error}
            notice={builder.notice}
            lastPublishedRevision={active.last_published_revision}
            consentDocuments={consentDocuments.documents}
            onSave={() => void builder.save()}
            onPublish={() => void builder.publish()}
            onExport={() => void builder.exportXlsx()}
            onImport={(file) => void builder.importXlsx(file)}
          />
        ) : (
          <div className="card">
            <div className="card-body">Загрузка черновика…</div>
          </div>
        )}
      </div>
    </div>
  );
}
