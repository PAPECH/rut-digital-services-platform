import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";

import { api } from "@/api/client";
import { useAuth } from "@/auth/AuthProvider";
import type { PublishedForm } from "@/entities/form/model/types";
import { formApi } from "@/features/forms/api/formApi";
import { trackAnalyticsEventOnce } from "@/features/analytics/api/analyticsApi";
import {
  initialFormValue,
  validateFormValue,
} from "@/features/forms/model/formValues";
import { FormFieldInputRegistry } from "@/features/forms/ui/fields/FormFieldInputRegistry";
import { usePlatform } from "@/features/platform-manifest/model/PlatformProvider";
import { getMissingProfileFields } from "@/features/profile-requirements/model/profileRequirements";
import { useI18n } from "@/i18n";
import { enableClosingConfirmation } from "@/max/bridge";

export function SubmitPage() {
  const { t } = useI18n();
  const { formId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const { profile } = useAuth();
  const { manifest } = usePlatform();
  const [form, setForm] = useState<PublishedForm | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const missing = getMissingProfileFields(
    profile,
    manifest?.bot.profile_schema,
  );
  const banForms = profile?.ban_forms ?? false;
  const numericFormId = Number(formId);
  const analyticsState = (location.state ?? {}) as {
    analyticsSource?: "category" | "form_catalog" | "direct";
    categoryId?: number;
    contentVersionId?: number;
    blockId?: string;
  };

  useEffect(() => {
    if (!Number.isInteger(numericFormId)) {
      setError(t("submit:error:loading_form"));
      return;
    }
    void formApi
      .get(numericFormId)
      .then((loaded) => {
        setForm(loaded);
        setValues(
          Object.fromEntries(
            loaded.fields
              .filter((field) => field.active)
              .map((field) => [field.key, initialFormValue(field, profile)]),
          ),
        );
        trackAnalyticsEventOnce(`form-open:${location.key}:${loaded.version_id}`, {
          action_type: "form_open",
          source_surface: analyticsState.analyticsSource ?? "direct",
          form_template_id: loaded.id,
          form_version_id: loaded.version_id,
          category_id: analyticsState.categoryId,
          content_version_id: analyticsState.contentVersionId,
          block_id: analyticsState.blockId,
        });
      })
      .catch((reason) =>
        setError(
          reason instanceof Error
            ? reason.message
            : t("submit:error:loading_form"),
        ),
      );
    enableClosingConfirmation();
  }, [
    analyticsState.analyticsSource,
    analyticsState.blockId,
    analyticsState.categoryId,
    analyticsState.contentVersionId,
    location.key,
    numericFormId,
    profile,
    t,
  ]);

  const idempotencyKey = useMemo(
    () => `${formId}:${Date.now()}:${Math.random()}`,
    [formId],
  );
  const onSubmit = async () => {
    if (!form) return;
    setError(null);
    if (banForms) {
      setError(profile?.ban_forms_reason || t("submit:error:form_ban"));
      return;
    }
    if (missing.length) {
      setError(`${t("submit:error:profile_empty")}: ${missing.join(", ")}`);
      return;
    }
    for (const field of form.fields.filter((item) => item.active)) {
      const message = validateFormValue(field, values[field.key]);
      if (message) {
        setError(message);
        return;
      }
    }
    setBusy(true);
    try {
      await api.post("/submissions", {
        form_template_id: form.id,
        form_version_id: form.version_id,
        values,
        idempotency_key: idempotencyKey,
      });
      navigate("/submissions", { replace: true });
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : t("submit:error:generic"),
      );
    } finally {
      setBusy(false);
    }
  };

  if (!form)
    return (
      <div className="screen">
        <h1 className="screen-title">{t("services:form:title")}</h1>
        {error ? (
          <div style={{ color: "var(--st-rej-fg)" }}>{error}</div>
        ) : (
          <div className="skeleton" style={{ width: "60%" }} />
        )}
      </div>
    );
  return (
    <div className="screen">
      <h1 className="screen-title">{form.name}</h1>
      {form.description ? (
        <p className="screen-sub">{form.description}</p>
      ) : null}
      {missing.length > 0 || banForms ? (
        <div
          style={{
            margin: "0 0 14px",
            padding: "10px 12px",
            borderRadius: 10,
            background: "var(--st-rej-bg)",
            color: "var(--st-rej-fg)",
            fontSize: 13,
            lineHeight: 1.45,
          }}
        >
          {banForms
            ? profile?.ban_forms_reason || t("services:main:ban_forms")
            : `${t("services:form:profile_incomplete")}: ${missing.join(", ")}.`}{" "}
          {!banForms ? (
            <button
              className="btn btn-sm"
              style={{ marginLeft: 6 }}
              onClick={() => navigate("/profile")}
            >
              {t("services:main:to_profile")}
            </button>
          ) : null}
        </div>
      ) : null}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {form.fields
          .filter((field) => field.active)
          .map((field) => (
            <FormFieldInputRegistry
              key={field.key}
              field={field}
              value={values[field.key]}
              disabled={busy}
              onChange={(value) => {
                trackAnalyticsEventOnce(`form-start:${location.key}:${form.version_id}`, {
                  action_type: "form_start",
                  source_surface: analyticsState.analyticsSource ?? "direct",
                  form_template_id: form.id,
                  form_version_id: form.version_id,
                  category_id: analyticsState.categoryId,
                  content_version_id: analyticsState.contentVersionId,
                  block_id: analyticsState.blockId,
                });
                setValues((current) => ({ ...current, [field.key]: value }));
              }}
            />
          ))}
      </div>
      {error ? (
        <div
          style={{
            margin: "16px 0",
            padding: "10px 12px",
            borderRadius: 10,
            background: "var(--st-rej-bg)",
            color: "var(--st-rej-fg)",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      ) : null}
      <div style={{ marginTop: 18 }}>
        <button
          className="btn btn-primary"
          disabled={busy || banForms || missing.length > 0}
          onClick={() => void onSubmit()}
        >
          {busy ? t("submit:button:loading") : t("submit:button:default")}
        </button>
      </div>
    </div>
  );
}
