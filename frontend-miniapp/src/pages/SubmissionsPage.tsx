import { SubmissionHistory } from "@/features/submissions/ui/SubmissionHistory";
import { useI18n } from "@/i18n";

export function SubmissionsPage() {
  const { t } = useI18n();
  return (
    <div className="screen">
      <h1 className="screen-title">{t("history:main:title")}</h1>
      <p className="screen-sub">{t("history:main:subtitle")}</p>
      <SubmissionHistory />
    </div>
  );
}
