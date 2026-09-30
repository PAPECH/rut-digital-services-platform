import { style } from "@vanilla-extract/css";

export const list = style({
  display: "grid",
  gap: "var(--space-3)",
});

export const addRow = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "var(--space-3)",
  padding: "var(--space-2) var(--space-3)",
  border: "1px dashed var(--line)",
  borderRadius: 10,
  fontSize: 13,
  color: "var(--ink-400)",
});

export const empty = style({
  padding: "var(--space-6)",
  textAlign: "center",
  color: "var(--ink-400)",
  border: "1px dashed var(--line)",
  borderRadius: 10,
});
