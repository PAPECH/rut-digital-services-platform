import { style } from "@vanilla-extract/css";

export const head = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  gap: "var(--space-3)",
  flexWrap: "wrap",
  marginBottom: "var(--space-3)",
});

export const hint = style({
  display: "block",
  fontSize: 12,
  color: "var(--ink-400)",
  maxWidth: 420,
});

export const list = style({
  display: "grid",
  gap: "var(--space-3)",
});

export const empty = style({
  padding: "var(--space-6)",
  textAlign: "center",
  color: "var(--ink-400)",
  border: "1px dashed var(--line)",
  borderRadius: 10,
});
