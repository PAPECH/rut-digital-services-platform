import { useState } from "react";
import { api } from "@/api/client";
import { useAuth } from "@/auth/AuthProvider";
import { revokeConsent } from "@/features/consent/api/consentApi";
import { useProfileEditor } from "@/features/profile-editing/model/useProfileEditor";
import { CoreProfileFields } from "@/features/profile-editing/ui/CoreProfileFields";
import { CustomProfileFields } from "@/features/profile-editing/ui/CustomProfileFields";
import { getMissingProfileFields } from "@/features/profile-requirements/model/profileRequirements";
import { usePlatform } from "@/features/platform-manifest/model/PlatformProvider";
import { useI18n } from "@/i18n";
import { requestContact } from "@/max/bridge";

interface ProfilePageProps {
  onShowPolicy: () => void;
}

export function ProfilePage({ onShowPolicy }: ProfilePageProps) {
  const { profile, refresh, insideMax } = useAuth();
  const { t } = useI18n();
  const { manifest } = usePlatform();
  const fields = manifest?.bot.profile_schema ?? [];
  const editor = useProfileEditor(fields);
  const [deleteConfirming, setDeleteConfirming] = useState(false);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  if (!profile) return null;

  const missing = getMissingProfileFields(profile, fields);

  const handleDeleteAccount = async () => {
    setDeleteBusy(true);
    setDeleteError(null);
    try {
      await revokeConsent();
      // App.tsx picks up !profile.consent_is_active after this and renders the
      // "account will be deleted on <date>" gate -- ProfilePage itself does not need to
      // render that state.
      await refresh();
    } catch (e) {
      setDeleteError((e as Error)?.message ?? "Не удалось удалить аккаунт");
      setDeleteBusy(false);
    }
  };

  const verifyPhone = async () => {
    try {
      const contact = await requestContact();
      await api.post("/auth/phone/verify", {
        phone: contact.phone,
        authDate: contact.authDate,
        hash: contact.hash,
        system: profile.system,
      });
      await refresh();
      editor.setMessage("Телефон подтверждён ✓");
    } catch (error) {
      editor.setMessage((error as Error)?.message ?? "Не удалось подтвердить телефон");
    }
  };

  return (
    <div className="screen">
      <h1 className="screen-title">{t("profile:main:title")}</h1>
      <p className="screen-sub">{t("profile:main:subtitle")}</p>

      {missing.length ? (
        <div className="profile-incomplete">
          {t("profile:main:incomplete")}: {missing.join(", ")}
        </div>
      ) : null}

      <div className="card">
        <CoreProfileFields value={editor.core} onChange={editor.setCore} />
        <CustomProfileFields
          fields={fields}
          values={editor.customData}
          onChange={editor.setCustomValue}
        />
        <div className="profile-save-actions">
          <button
            className="btn btn-primary"
            disabled={!editor.canSave}
            onClick={() => void editor.save()}
          >
            {editor.busy ? t("profile:main:saving") : t("profile:main:save")}
          </button>
        </div>
        {editor.message ? <div className="profile-message">{editor.message}</div> : null}
      </div>

      <div className="card">
        <div className="row">
          <span className="lbl">{t("profile:main:phone")}</span>
          <span className="val">
            {profile.phone ? profile.phone : t("profile:main:phone_unverified")}
            {profile.phone_verified ? <span className="profile-phone-ok">✓</span> : null}
          </span>
        </div>
        {!profile.phone_verified && insideMax ? (
          <button className="btn btn-secondary" onClick={() => void verifyPhone()}>
            {t("profile:main:verify_phone")}
          </button>
        ) : null}
        {!profile.phone_verified && !insideMax ? (
          <div className="profile-phone-hint">
            {t("profile:main:phone_verification_not_available")}
          </div>
        ) : null}
      </div>

      <div className="card">
        <div className="row" style={{ borderBottom: 'none'}}>
          <span className="lbl">Положение о работе с персональными данными</span>
        </div>
        <button className="btn btn-secondary" onClick={onShowPolicy}>
          Посмотреть документ
        </button>
      </div>

      <div className="card">
        {deleteConfirming ? (
          <>
            <p style={{ margin: "0 0 12px", fontSize: 14, lineHeight: 1.5 }}>
              Согласие на обработку персональных данных будет отозвано, бот и мини-приложение
              станут недоступны сразу. Аккаунт и все данные (сообщения, заявки) будут
              окончательно удалены через 10 рабочих дней, если вы не подтвердите согласие
              повторно за это время.
            </p>
            {deleteError ? (
              <p style={{ color: "var(--st-rej-fg, #b91c1c)", fontSize: 13 }}>{deleteError}</p>
            ) : null}
            <div style={{ display: "flex", gap: 8 }}>
              <button
                className="btn btn-secondary"
                disabled={deleteBusy}
                onClick={() => setDeleteConfirming(false)}
              >
                Отмена
              </button>
              <button
                className="btn btn-danger"
                disabled={deleteBusy}
                onClick={() => void handleDeleteAccount()}
              >
                {deleteBusy ? "Отзываем…" : "Да, отозвать согласие"}
              </button>
            </div>
          </>
        ) : (
          <button className="btn btn-danger" onClick={() => setDeleteConfirming(true)}>
            Отозвать согласие на обработку персональных данных
          </button>
        )}
      </div>
    </div>
  );
}
