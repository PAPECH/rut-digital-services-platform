import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import type { ApiError } from "@/api/client";
import { useAuth } from "@/auth/AuthProvider";
import type {
  PublishedTestDetail,
  TestAttempt,
} from "@/entities/form-test/model/types";
import { formTestApi } from "@/features/form-tests/api/formTestApi";
import { splitConsentCheckboxText } from "@/features/form-tests/lib/consentPlaceholder";
import { groupElements, isQuestionGroup } from "@/features/form-tests/model/groupElements";
import { numberElements } from "@/features/form-tests/model/numbering";
import { getMissingTestProfileFields } from "@/features/form-tests/model/profileRequirements";
import { useAutosave } from "@/features/form-tests/model/useAutosave";
import { ElementGroupRegistry } from "@/features/form-tests/ui/elements/ElementGroupRegistry";
import { TestConsentDocumentScreen } from "@/features/form-tests/ui/TestConsentDocumentScreen";
import { TestResultScreen } from "@/features/form-tests/ui/TestResultScreen";
import { usePlatform } from "@/features/platform-manifest/model/PlatformProvider";
import { useI18n } from "@/i18n";
import * as styles from "./TestPage.css";

function completionErrorMessage(error: unknown, fallback: string, consentRequiredMessage: string): string {
  const apiError = error as ApiError;
  if (apiError.code === "missing_required_answer") {
    return "Ответьте на все обязательные вопросы перед завершением.";
  }
  if (apiError.code === "invalid_test_answer") {
    return "Один из ответов имеет неверный формат.";
  }
  if (apiError.code === "consent_required") {
    return consentRequiredMessage;
  }
  return error instanceof Error ? error.message : fallback;
}

export function TestPage() {
  const { t } = useI18n();
  const { testId } = useParams();
  const navigate = useNavigate();
  // Completing a test can be reached from a content category block, the Services catalog,
  // or a direct deep link -- there's no single "correct" destination page to hardcode, so
  // go back the way the user came in and only fall back to home when there's no prior
  // in-app entry to return to (idx 0 means this is the first history entry the app pushed).
  const navigateBack = useCallback(() => {
    const historyState = window.history.state as { idx?: number } | null;
    if (historyState?.idx) {
      navigate(-1);
    } else {
      navigate("/");
    }
  }, [navigate]);
  const [searchParams, setSearchParams] = useSearchParams();
  const numericTestId = Number(testId);
  // Set only when arriving from the attempt-history list on a specific, already-completed
  // attempt (Task 075) -- loads that exact attempt read-only via `getAttempt` instead of
  // resuming/starting through `startAttempt`. Resuming an in-progress historical row still goes
  // through the plain start flow below, unaffected.
  const viewAttemptParam = searchParams.get("attempt");
  const numericViewAttemptId = viewAttemptParam ? Number(viewAttemptParam) : null;

  // Task 080: the anketa no longer asks for name/birth date/email itself -- a student's profile
  // must have them before starting or resuming an attempt. Viewing an already-completed historical
  // attempt (`numericViewAttemptId != null`, reached via `getAttempt`, never `startAttempt`) is
  // never gated -- they already finished it. `TestCatalog`/content blocks already redirect to
  // `/profile` before reaching this page in the normal flow; this covers a direct deep link that
  // bypasses the catalog (e.g. a `test_action` content block).
  const { profile } = useAuth();
  const { manifest } = usePlatform();
  const missingProfileFields = useMemo(
    () => getMissingTestProfileFields(profile, manifest?.bot.profile_schema),
    [manifest?.bot.profile_schema, profile],
  );
  const profileIncomplete = numericViewAttemptId == null && missingProfileFields.length > 0;

  const [test, setTest] = useState<PublishedTestDetail | null>(null);
  const [attempt, setAttempt] = useState<TestAttempt | null>(null);
  const [answers, setAnswers] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<string | null>(null);
  const [completing, setCompleting] = useState(false);
  const [justSaved, setJustSaved] = useState(false);
  const [consentChecked, setConsentChecked] = useState(false);
  const [showConsentDoc, setShowConsentDoc] = useState(false);

  useEffect(() => {
    if (!Number.isInteger(numericTestId)) {
      setError(t("tests:page:loading_error"));
      return;
    }
    if (profileIncomplete) return;
    let mounted = true;
    const loadAttempt =
      numericViewAttemptId != null
        ? formTestApi.getAttempt(numericViewAttemptId)
        : formTestApi.startAttempt(numericTestId);
    void Promise.all([formTestApi.get(numericTestId), loadAttempt])
      .then(([loadedTest, loadedAttempt]) => {
        if (!mounted) return;
        setTest(loadedTest);
        setAttempt(loadedAttempt);
        setAnswers(loadedAttempt.answers);
      })
      .catch((reason: unknown) => {
        if (mounted) {
          setError(reason instanceof Error ? reason.message : t("tests:page:loading_error"));
        }
      });
    return () => {
      mounted = false;
    };
  }, [numericTestId, numericViewAttemptId, profileIncomplete, t]);

  const handleRetake = useCallback(async () => {
    const fresh = await formTestApi.retake(numericTestId);
    setAttempt(fresh);
    setAnswers(fresh.answers);
    setConsentChecked(false);
    if (viewAttemptParam) {
      setSearchParams({}, { replace: true });
    }
  }, [numericTestId, viewAttemptParam, setSearchParams]);

  const saveAnswers = useCallback(
    async (changed: Record<string, unknown>) => {
      if (!attempt) return;
      await formTestApi.autosave(attempt.id, changed);
      setJustSaved(true);
      window.setTimeout(() => setJustSaved(false), 2000);
    },
    [attempt],
  );
  useAutosave(answers, saveAnswers, Boolean(attempt) && attempt?.status === "in_progress");

  const groups = useMemo(
    () => (test ? groupElements(test.elements) : []),
    [test],
  );
  const numberByKey = useMemo(
    () => (test ? numberElements(test.elements) : new Map<string, number>()),
    [test],
  );

  const onAnswerChange = (key: string, value: unknown) => {
    setAnswers((current) => ({ ...current, [key]: value }));
  };

  const onComplete = async () => {
    if (!attempt) return;
    setError(null);
    setCompleting(true);
    try {
      await formTestApi.autosave(attempt.id, answers);
      const completed = await formTestApi.complete(attempt.id, consentChecked);
      setAttempt(completed);
    } catch (reason) {
      setError(
        completionErrorMessage(
          reason,
          t("tests:page:loading_error"),
          t("tests:page:consent_required_error"),
        ),
      );
    } finally {
      setCompleting(false);
    }
  };

  if (profileIncomplete) {
    return (
      <div className="screen test-page-screen">
        <h1 className="screen-title">{t("tests:catalog:title")}</h1>
        <div className={styles.errorBanner}>
          {t("tests:page:profile_incomplete")}: {missingProfileFields.join(", ")}.
        </div>
        <button className="btn btn-primary" onClick={() => navigate("/profile")}>
          {t("services:main:to_profile")}
        </button>
      </div>
    );
  }

  if (error && !test) {
    return (
      <div className="screen test-page-screen">
        <h1 className="screen-title">{t("tests:catalog:title")}</h1>
        <div className={styles.errorBanner}>{error}</div>
      </div>
    );
  }

  if (!test || !attempt) {
    return (
      <div className="screen test-page-screen">
        <h1 className="screen-title">{t("tests:catalog:title")}</h1>
        <div className="skeleton" style={{ width: "60%" }} />
      </div>
    );
  }

  if (showConsentDoc) {
    return (
      <TestConsentDocumentScreen
        testId={numericTestId}
        title={test.consent_document_title ?? test.name}
        onBack={() => setShowConsentDoc(false)}
      />
    );
  }

  if (attempt.status === "completed") {
    return (
      <TestResultScreen
        test={test}
        attempt={attempt}
        onRetake={test.allow_retake ? handleRetake : undefined}
        onBack={() => navigateBack()}
      />
    );
  }

  return (
    <div className="screen test-page-screen">
      <h1 className="screen-title">{test.name}</h1>
      {test.intro_text ? <p className="screen-sub">{test.intro_text}</p> : null}

      <div className={styles.list}>
        {groups.map((group, index) => {
          const key = group.kind === "single" ? group.element.key : `matrix-${index}`;
          const showDivider = index > 0 && isQuestionGroup(group) && isQuestionGroup(groups[index - 1]);
          return (
            <Fragment key={key}>
              {showDivider ? <hr className={styles.divider} /> : null}
              <ElementGroupRegistry
                group={group}
                numberByKey={numberByKey}
                answers={answers}
                disabled={completing}
                onChange={onAnswerChange}
              />
            </Fragment>
          );
        })}
      </div>

      {error ? <div className={styles.errorBanner}>{error}</div> : null}

      {test.consent_enabled ? (
        <label className={styles.consentRow}>
          <input
            type="checkbox"
            className={styles.consentCheckbox}
            checked={consentChecked}
            disabled={completing}
            onChange={(event) => setConsentChecked(event.target.checked)}
          />
          <span>
            {splitConsentCheckboxText(test.consent_checkbox_text ?? "").map((part, index, parts) => (
              <Fragment key={index}>
                {part}
                {index < parts.length - 1 ? (
                  <button
                    type="button"
                    className={styles.consentLink}
                    onClick={() => setShowConsentDoc(true)}
                  >
                    {test.consent_document_title ?? "документ"}
                  </button>
                ) : null}
              </Fragment>
            ))}
          </span>
        </label>
      ) : null}

      <div className={styles.footer}>
        <button
          className="btn btn-primary"
          disabled={completing || (test.consent_enabled && !consentChecked)}
          onClick={() => void onComplete()}
        >
          {completing ? t("tests:page:completing") : t("tests:page:complete_button")}
        </button>
        {justSaved ? (
          <span className={styles.autosaveHint}>{t("tests:page:progress_saved")}</span>
        ) : null}
      </div>
    </div>
  );
}
