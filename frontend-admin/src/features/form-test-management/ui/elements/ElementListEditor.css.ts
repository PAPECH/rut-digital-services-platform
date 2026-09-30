import { style } from "@vanilla-extract/css";

export const head = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "var(--space-3)",
  flexWrap: "wrap",
  marginBottom: "var(--space-3)",
});

export const hint = style({
  display: "block",
  fontSize: 12,
  color: "var(--ink-400)",
});

export const list = style({
  display: "grid",
  gap: "var(--space-3)",
});

export const addRow = style({
  display: "flex",
  alignItems: "center",
  gap: "var(--space-2)",
  marginTop: "var(--space-3)",
  paddingTop: "var(--space-3)",
  borderTop: "1px solid var(--line)",
});

export const empty = style({
  display: "grid",
  gap: "var(--space-1)",
  padding: "var(--space-6)",
  textAlign: "center",
  color: "var(--ink-400)",
  border: "1px dashed var(--line)",
  borderRadius: 10,
});
