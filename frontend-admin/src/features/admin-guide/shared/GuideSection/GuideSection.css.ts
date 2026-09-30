import { style } from "@vanilla-extract/css";

export const section = style({
  display: "grid",
  gap: "var(--space-4)",
  padding: "var(--space-6)",
  border: "1px solid var(--line)",
  borderRadius: "var(--r-lg)",
  background: "var(--card)",
  scrollMarginTop: 80,
  "@media": { "(max-width: 767px)": { padding: "var(--space-4)" } },
});

export const title = style({
  margin: 0,
  fontSize: 20,
  fontWeight: 700,
  color: "var(--ink-900)",
});

export const lead = style({
  margin: 0,
  color: "var(--ink-500)",
  fontSize: 14,
  lineHeight: 1.6,
  maxWidth: 760,
});
