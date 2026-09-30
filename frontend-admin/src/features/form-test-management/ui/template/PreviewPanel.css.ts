import { style } from "@vanilla-extract/css";

export const wrapper = style({
  marginTop: "var(--space-3)",
  padding: "var(--space-3)",
  border: "1px dashed var(--line)",
  borderRadius: 10,
  display: "grid",
  gap: "var(--space-3)",
});

export const head = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  fontSize: 12.5,
  color: "var(--ink-400)",
});

export const grid = style({
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
  gap: "var(--space-2)",
});

export const field = style({
  display: "grid",
  gap: "var(--space-1)",
  fontSize: 12,
  color: "var(--ink-400)",
});

export const error = style({
  color: "var(--danger-600, #b42318)",
  fontSize: 13,
});

export const result = style({
  display: "grid",
  gap: "var(--space-2)",
});

export const resultMeta = style({
  fontSize: 12.5,
  color: "var(--ink-400)",
});

export const chunk = style({
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
  background: "var(--surface-200, #f1f3f5)",
  borderRadius: 8,
  padding: "var(--space-3)",
  fontFamily: "inherit",
  fontSize: 13,
});
