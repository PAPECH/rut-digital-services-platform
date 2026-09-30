/** The one fixed link placeholder a published test's consent checkbox text may contain --
 * mirrors `frontend-admin`'s `lib/consentPlaceholder.ts` (same literal token, same reasoning: a
 * checkbox references exactly one document, so there is no per-key syntax to parse). */
export const CONSENT_DOCUMENT_LINK_PLACEHOLDER = "{{consent_document_link}}";

export function splitConsentCheckboxText(text: string): string[] {
  return text.split(CONSENT_DOCUMENT_LINK_PLACEHOLDER);
}
