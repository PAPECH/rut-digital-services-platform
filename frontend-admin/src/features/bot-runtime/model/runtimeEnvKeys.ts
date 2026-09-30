function slugSuffix(slug: string): string {
  return slug
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function runtimeTokenEnvKey(slug: string): string {
  return `BOT_RUNTIME_TOKEN_${slugSuffix(slug)}`;
}

export function webhookSecretEnvKey(slug: string): string {
  return `BOT_WEBHOOK_SECRET_${slugSuffix(slug)}`;
}
