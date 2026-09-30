import { style } from "@vanilla-extract/css";

export const hint = style({
  fontSize: 12.5,
  color: "var(--ink-400)",
  lineHeight: 1.6,
});

export const warning = style({
  fontSize: 12.5,
  color: "var(--st-work-fg, #8a5400)",
  background: "var(--st-work-bg, #fff1d6)",
  borderRadius: 8,
  padding: "var(--space-2) var(--space-3)",
  marginTop: "var(--space-2)",
});
