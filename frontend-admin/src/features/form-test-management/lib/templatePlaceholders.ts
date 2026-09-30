const PLACEHOLDER_RE = /\{\{result:([A-Za-z0-9_-]+)\.(value|label|recommendation)\}\}/g;
const FLAGGED_BLOCK_RE = /\{\{#flagged:([A-Za-z0-9_-]+)\}\}/g;

export type PlaceholderField = "value" | "label" | "recommendation";

export function placeholderFor(key: string, field: PlaceholderField): string {
  return `{{result:${key}.${field}}}`;
}

export function flaggedBlockFor(key: string, body: string): string {
  return `{{#flagged:${key}}}${body}{{/flagged:${key}}}`;
}

/** Every result-scale key the template actually references, via either a `{{result:...}}`
 * placeholder or a `{{#flagged:...}}` block -- used to warn about a key that doesn't (or no
 * longer) exists, before the admin finds out the hard way at publish time. */
export function referencedKeys(template: string): Set<string> {
  const keys = new Set<string>();
  for (const match of template.matchAll(PLACEHOLDER_RE)) keys.add(match[1]);
  for (const match of template.matchAll(FLAGGED_BLOCK_RE)) keys.add(match[1]);
  return keys;
}

export function unknownKeys(template: string, knownKeys: Set<string>): string[] {
  return [...referencedKeys(template)].filter((key) => !knownKeys.has(key)).sort();
}
