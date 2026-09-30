import { style } from "@vanilla-extract/css";

export const list = style({
  display: "grid",
  gap: "var(--space-2)",
});

export const toggle = style({
  display: "flex",
  alignItems: "center",
  gap: "var(--space-2)",
  fontSize: 13.5,
  fontWeight: 600,
  cursor: "pointer",
});

export const hint = style({
  fontSize: 12.5,
  color: "var(--ink-400)",
  fontWeight: 400,
  marginLeft: "calc(var(--space-2) + 16px)",
});
