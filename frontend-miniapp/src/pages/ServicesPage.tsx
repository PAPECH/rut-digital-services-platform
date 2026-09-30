import { FormCatalog } from "@/features/forms/ui/FormCatalog";
import { TestCatalog } from "@/features/form-tests/ui/TestCatalog";
import { useI18n } from "@/i18n";

export function ServicesPage() {
  const { t } = useI18n();
  return (
    <div className="screen">
      <h1 className="screen-title">{t("services:main:services")}</h1>
      <p className="screen-sub">{t("services:main:services_sub")}</p>

      <FormCatalog title={t("services:main:available_forms")} />
      <TestCatalog title={t("tests:catalog:title")} />
    </div>
  );
}
