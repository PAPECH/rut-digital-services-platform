import type { CampaignLinkTarget } from "@/entities/campaign-links/model/types";

export const WEBAPP_CODE_MAX_LENGTH = 512;
export const BOT_CODE_MAX_LENGTH = 128;

const CODE_RE = /^[A-Za-z0-9_-]+$/;

/** Mirrors `validate_code` in `app.modules.campaign_links.domain.entities` — kept in sync by
 * hand since this is a thin client-side echo of a server rule, not the source of truth. */
export function codeValidationError(
  code: string,
  target: CampaignLinkTarget,
): string | null {
  const trimmed = code.trim();
  if (!trimmed) return "Код не может быть пустым";
  if (!CODE_RE.test(trimmed)) {
    return "Код может содержать только латинские буквы, цифры, «_» и «-»";
  }
  const limit = target === "bot" ? BOT_CODE_MAX_LENGTH : WEBAPP_CODE_MAX_LENGTH;
  if (trimmed.length > limit) {
    return target === "bot"
      ? `Код длиннее ${BOT_CODE_MAX_LENGTH} символов, допустимых для перехода в чат бота`
      : `Код длиннее ${WEBAPP_CODE_MAX_LENGTH} символов`;
  }
  return null;
}

function slugifyPart(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/gi, "-")
    .replace(/^-+|-+$/g, "");
}

export function suggestCode(campaign: string, source: string, placement: string): string {
  return [campaign, source, placement]
    .map(slugifyPart)
    .filter(Boolean)
    .join("-")
    .slice(0, WEBAPP_CODE_MAX_LENGTH);
}
