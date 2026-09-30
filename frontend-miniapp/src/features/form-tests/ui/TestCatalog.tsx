import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "@/auth/AuthProvider";
import { Icon } from "@/components/Icon";
import type { PublishedTestSummary } from "@/entities/form-test/model/types";
import { formTestApi } from "@/features/form-tests/api/formTestApi";
import { getMissingTestProfileFields } from "@/features/form-tests/model/profileRequirements";
import { usePlatform } from "@/features/platform-manifest/model/PlatformProvider";
import { useI18n } from "@/i18n";

export function TestCatalog({ title }: { title?: string | null }) {
  const { t } = useI18n();
  const { profile } = useAuth();
  const { manifest } = usePlatform();
  const navigate = useNavigate();
  const [tests, setTests] = useState<PublishedTestSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setError(null);
    void formTestApi
      .list()
      .then((items) => {
        if (mounted) setTests(items);
      })
      .catch((loadError: unknown) => {
        if (mounted) {
          setError(
            loadError instanceof Error ? loadError.message : t("tests:catalog:error"),
          );
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, [t]);

  const isComplete = useMemo(
    () => getMissingTestProfileFields(profile, manifest?.bot.profile_schema).length === 0,
    [manifest?.bot.profile_schema, profile],
  );

  const openTest = (testId: number) => {
    if (!isComplete) {
      navigate("/profile");
      return;
    }
    navigate(`/tests/${testId}`);
  };

  return (
    <section className="embedded-system-block test-catalog-block">
      <h3 className="section-label">{title ?? t("tests:catalog:title")}</h3>
      {!isComplete ? (
        <button
          type="button"
          className="card profile-required-card"
          onClick={() => navigate("/profile")}
        >
          {t("tests:catalog:profile_incomplete")}
        </button>
      ) : null}
      {loading ? (
        <div className="card embedded-system-state">{t("tests:catalog:loading")}</div>
      ) : null}
      {error ? <div className="card form-error">{error}</div> : null}
      {!loading && !error && tests.length === 0 ? (
        <div className="card muted">{t("tests:catalog:empty")}</div>
      ) : null}
      {!loading && !error
        ? tests.map((test) => (
            <button
              key={test.id}
              type="button"
              className="card service-form-card cms-form-action"
              onClick={() => openTest(test.id)}
            >
              <span>
                <strong>{test.name}</strong>
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
