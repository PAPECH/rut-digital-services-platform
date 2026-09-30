const selectedBotStorageKey = "platform.admin.bot-slug";
const defaultBotSlug = "default";

export function getSelectedBotSlug(): string {
  return localStorage.getItem(selectedBotStorageKey) || defaultBotSlug;
}

export function persistSelectedBotSlug(slug: string): void {
  localStorage.setItem(selectedBotStorageKey, slug);
}
