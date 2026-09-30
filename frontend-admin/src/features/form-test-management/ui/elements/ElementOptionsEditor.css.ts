import { style } from "@vanilla-extract/css";

export const wrapper = style({
  display: "grid",
  gap: "var(--space-2)",
  marginTop: "var(--space-2)",
  padding: "var(--space-2) var(--space-3)",
  border: "1px dashed var(--line)",
  borderRadius: 8,
});

export const head = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  fontSize: 12.5,
  color: "var(--ink-400)",
});

export const row = style({
  display: "grid",
  gridTemplateColumns: "minmax(0, 1fr) minmax(0, 2fr) 90px auto",
  gap: "var(--space-2)",
  alignItems: "center",
});

export const actions = style({
  display: "flex",
  gap: "var(--space-1)",
});

export const empty = style({
  fontSize: 12.5,
  color: "var(--ink-400)",
  padding: "var(--space-1) 0",
});
