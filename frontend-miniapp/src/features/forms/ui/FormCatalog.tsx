import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "@/auth/AuthProvider";
import { Icon } from "@/components/Icon";
import type { PublishedFormSummary } from "@/entities/form/model/types";
import { formApi } from "@/features/forms/api/formApi";
import { usePlatform } from "@/features/platform-manifest/model/PlatformProvider";
import { getMissingProfileFields } from "@/features/profile-requirements/model/profileRequirements";
import { useI18n } from "@/i18n";

interface FormCatalogAnalyticsContext {
  categoryId: number;
  contentVersionId: number;
  blockId: string;
}

export function FormCatalog({
  title,
  analyticsContext,
}: {
  title?: string | null;
  analyticsContext?: FormCatalogAnalyticsContext;
}) {
  const { t } = useI18n();
  const { profile } = useAuth();
  const { manifest } = usePlatform();
  const navigate = useNavigate();
  const [forms, setForms] = useState<PublishedFormSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    void formApi
      .list()
      .then((items) => {
        if (mounted) setForms(items);
      })
      .catch((loadError: unknown) => {
        if (mounted)
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Не удалось загрузить формы",
          );
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const isComplete = useMemo(
    () =>
      getMissingProfileFields(profile, manifest?.bot.profile_schema).length ===
      0,
    [manifest?.bot.profile_schema, profile],
  );
  const banForms = profile?.ban_forms ?? false;

  const openForm = (formId: number) => {
    if (banForms) return;
    if (!isComplete) {
      navigate("/profile");
      return;
    }
    const form = forms.find((item) => item.id === formId);
    navigate(`/submit/${formId}`, {
      state: {
        analyticsSource: analyticsContext ? "category" : "form_catalog",
        categoryId: analyticsContext?.categoryId,
        contentVersionId: analyticsContext?.contentVersionId,
        blockId: analyticsContext?.blockId,
        formVersionId: form?.version_id,
      },
    });
  };

  return (
    <section className="embedded-system-block form-catalog-block">
      {title ? <h3 className="section-label">{title}</h3> : null}
      {!isComplete && !banForms ? (
        <button
          type="button"
          className="card profile-required-card"
          onClick={() => navigate("/profile")}
        >
          {t("services:main:profile_incomplete")}
        </button>
      ) : null}
      {banForms ? (
        <div className="card form-error">
          {t("services:main:ban_forms")}
          {profile?.ban_forms_reason
            ? ` ${t("word:reason")}: ${profile.ban_forms_reason}`
            : ""}
        </div>
      ) : null}
      {loading ? (
        <div className="card embedded-system-state">Загрузка форм…</div>
      ) : null}
      {error ? (
        <div className="card form-error">{error}</div>
      ) : null}
      {!loading && !error && forms.length === 0 ? (
        <div className="card muted">{t("services:main:no_forms")}</div>
      ) : null}
      {!loading && !error
        ? forms.map((form) => (
            <button
              key={form.id}
              type="button"
              className="card service-form-card cms-form-action"
              disabled={banForms}
              onClick={() => openForm(form.id)}
            >
              <span>
                <strong>{form.name}</strong>
                {form.description ? <small>{form.description}</small> : null}
              </span>
              <span className="ico" aria-hidden="true">
                <Icon.ChevronRight />
              </span>
            </button>
          ))
        : null}
    </section>
  );
}
