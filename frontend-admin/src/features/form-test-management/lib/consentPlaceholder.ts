/** The one fixed link placeholder a consent checkbox's text may contain -- unlike the result
 * template's `{{result:<key>.field}}` syntax, a checkbox references exactly one document (picked
 * from a dropdown), so there is no per-key variant to build or scan for. */
export const CONSENT_DOCUMENT_LINK_PLACEHOLDER = "{{consent_document_link}}";

export function consentCheckboxTextHasLink(text: string): boolean {
  return text.includes(CONSENT_DOCUMENT_LINK_PLACEHOLDER);
}

/** Splits the checkbox text around the link placeholder for preview/rendering -- the parts
 * between which a document-link control should be inserted. */
export function splitConsentCheckboxText(text: string): string[] {
  return text.split(CONSENT_DOCUMENT_LINK_PLACEHOLDER);
}
