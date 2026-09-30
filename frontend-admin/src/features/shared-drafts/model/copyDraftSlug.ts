export function copyDraftSlug(source: string, existingSlugs: Set<string>): string {
  const base = `${source.slice(0, 70)}-copy`;
  if (!existingSlugs.has(base)) return base;
  for (let suffix = 2; suffix < 100; suffix += 1) {
    const candidate = `${source.slice(0, 68)}-${suffix}`;
    if (!existingSlugs.has(candidate)) return candidate;
  }
  return `${source.slice(0, 64)}-${Date.now().toString().slice(-6)}`;
}
