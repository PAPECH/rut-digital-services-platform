import { useEffect, useState } from "react";

import type {
  CampaignLinkCreateInput,
  CampaignLinkTarget,
} from "@/entities/campaign-links/model/types";
import {
  codeValidationError,
  suggestCode,
} from "@/features/campaign-links/model/validation";

interface Props {
  creating: boolean;
  onCreate: (
    input: CampaignLinkCreateInput,
  ) => Promise<{ ok: true } | { ok: false; message: string; code?: string }>;
}

export function CampaignLinkForm({ creating, onCreate }: Props) {
  const [campaign, setCampaign] = useState("");
  const [source, setSource] = useState("");
  const [placement, setPlacement] = useState("");
  const [target, setTarget] = useState<CampaignLinkTarget>("webapp");
  const [code, setCode] = useState("");
  const [codeTouched, setCodeTouched] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!codeTouched) setCode(suggestCode(campaign, source, placement));
  }, [campaign, source, placement, codeTouched]);

  const codeError = code ? codeValidationError(code, target) : null;
  const canSubmit =
    campaign.trim() && source.trim() && placement.trim() && code.trim() && !codeError;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!canSubmit) return;
    setSubmitError(null);
    const result = await onCreate({
      code: code.trim(),
      campaign: campaign.trim(),
      source: source.trim(),
      placement: placement.trim(),
      target,
    });
    if (result.ok) {
      setCampaign("");
      setSource("");
      setPlacement("");
      setCode("");
      setCodeTouched(false);
    } else {
      setSubmitError(result.message);
    }
  };

  return (
    <form className="campaign-links-form" onSubmit={handleSubmit}>
      <div className="campaign-links-form-row">
        <label>
          Кампания
          <input
            className="input"
            value={campaign}
            onChange={(e) => setCampaign(e.target.value)}
            placeholder="Приёмная кампания 2026"
            required
          />
        </label>
        <label>
          Источник
          <input
            className="input"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            placeholder="vk"
            required
          />
        </label>
        <label>
          Размещение
          <input
            className="input"
            value={placement}
            onChange={(e) => setPlacement(e.target.value)}
            placeholder="story"
            required
          />
        </label>
      </div>
      <div className="campaign-links-form-row">
        <label>
          Куда ведёт
          <select
            className="input"
            value={target}
            onChange={(e) => setTarget(e.target.value as CampaignLinkTarget)}
          >
            <option value="webapp">Мини-приложение</option>
            <option value="bot">Чат бота</option>
          </select>
        </label>
        <label className="campaign-links-form-code">
          Код ссылки
          <input
            className="input"
            value={code}
            onChange={(e) => {
              setCode(e.target.value);
              setCodeTouched(true);
            }}
            placeholder="promo-vk-story"
            required
          />
        </label>
      </div>
      {codeError ? <p className="form-error">{codeError}</p> : null}
      {submitError ? <p className="form-error">{submitError}</p> : null}
      <button type="submit" className="btn btn-primary" disabled={!canSubmit || creating}>
        {creating ? "Создание…" : "Создать ссылку"}
      </button>
    </form>
  );
}
