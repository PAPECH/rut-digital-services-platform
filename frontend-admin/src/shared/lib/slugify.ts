const CYRILLIC_TRANSLIT: Record<string, string> = {
  а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "e", ж: "zh", з: "z",
  и: "i", й: "y", к: "k", л: "l", м: "m", н: "n", о: "o", п: "p", р: "r",
  с: "s", т: "t", у: "u", ф: "f", х: "h", ц: "ts", ч: "ch", ш: "sh", щ: "sch",
  ъ: "", ы: "y", ь: "", э: "e", ю: "yu", я: "ya",
};

/** Transliterates Cyrillic, lowercases, and collapses anything else into single dashes --
 * the one slug-derivation rule every "auto-fill from name, editable after" field in this
 * admin shares, so a Russian title never collapses to an empty or truncated-looking slug. */
export function slugify(value: string, maxLength = 80): string {
  const transliterated = value
    .toLowerCase()
    .split("")
    .map((char) => CYRILLIC_TRANSLIT[char] ?? char)
    .join("");
  return transliterated
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, maxLength);
}
