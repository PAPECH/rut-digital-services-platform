import { style, styleVariants } from "@vanilla-extract/css";

export const panel = style({
  display: "grid",
  gap: "var(--space-3)",
  alignContent: "start",
  minWidth: 0,
});

export const label = style({
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  justifySelf: "start",
  padding: "3px 10px",
  borderRadius: 999,
  fontSize: 12,
  fontWeight: 700,
  letterSpacing: "0.02em",
});

export const labelTone = styleVariants({
  steps: { background: "var(--ink-50)", color: "var(--ink-500)" },
  admin: { background: "var(--brand-50)", color: "var(--brand)" },
  result: { background: "var(--st-done-bg)", color: "var(--st-done-fg)" },
});

export const hint = style({ margin: 0, color: "var(--ink-400)", fontSize: 12.5 });
