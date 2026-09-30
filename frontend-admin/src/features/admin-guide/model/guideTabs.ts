/**
 * Tabs of the admin «Инструкции» page (Task 087). Each tab documents one admin section.
 *
 * `updatedAt` is the «Актуально на» date printed at the bottom of the tab. Per the guardrails,
 * a change that alters functionality a tab describes must update that tab and this date.
 */
export type GuideTabKey = "content" | "forms";

export interface GuideTabDefinition {
  key: GuideTabKey;
  label: string;
  updatedAt: string;
}

export const GUIDE_TABS: ReadonlyArray<GuideTabDefinition> = [
  { key: "content", label: "Контент", updatedAt: "2026-09-29" },
  { key: "forms", label: "Конструктор форм", updatedAt: "2026-09-29" },
];

export const DEFAULT_GUIDE_TAB: GuideTabKey = "content";

export function parseGuideTab(value: string | null): GuideTabKey {
  return GUIDE_TABS.some((tab) => tab.key === value) ? (value as GuideTabKey) : DEFAULT_GUIDE_TAB;
}

export function guideTab(key: GuideTabKey): GuideTabDefinition {
  return GUIDE_TABS.find((tab) => tab.key === key) ?? GUIDE_TABS[0];
}
