function resolvePath(context: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((value, key) => {
    if (value && typeof value === "object" && key in value) {
      return (value as Record<string, unknown>)[key];
    }
    return undefined;
  }, context);
}

/**
 * Minimal `{{ dotted.path }}` substitution for admin-authored CMS text (home-screen greeting
 * title/subtitle). A `, ` immediately before a placeholder collapses together with it when the
 * resolved value is empty, so an admin template like "Здравствуйте, {{ profile.first_name }}!"
 * degrades to "Здравствуйте!" for a user with no first name instead of leaving a dangling ", ".
 */
export function renderTemplate(template: string, context: Record<string, unknown>): string {
  return template.replace(/,?\s*\{\{\s*([\w.]+)\s*\}\}/g, (match, path: string) => {
    const value = resolvePath(context, path);
    if (value === null || value === undefined || value === "") return "";
    return match.startsWith(",") ? `, ${String(value)}` : String(value);
  });
}
