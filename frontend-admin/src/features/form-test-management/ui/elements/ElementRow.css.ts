import { style } from "@vanilla-extract/css";

export const row = style({
  border: "1px solid var(--line)",
  borderRadius: 10,
  padding: "var(--space-3)",
  display: "grid",
  gap: "var(--space-2)",
});

export const header = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "var(--space-3)",
});

export const identity = style({
  display: "flex",
  alignItems: "center",
  gap: "var(--space-3)",
  flex: "1 1 auto",
  minWidth: 0,
});

export const number = style({
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: 22,
  height: 22,
  borderRadius: "50%",
  background: "var(--surface-200, #f1f3f5)",
  fontSize: 12,
  flexShrink: 0,
});

export const key = style({
  display: "block",
  color: "var(--ink-400)",
  fontSize: 11.5,
});

export const actions = style({
  display: "flex",
  gap: "var(--space-2)",
  flex: "0 0 auto",
  flexWrap: "wrap",
});

export const settings = style({
  display: "grid",
  gap: "var(--space-3)",
  paddingTop: "var(--space-2)",
  borderTop: "1px solid var(--line)",
});

export const field = style({
  display: "grid",
  gap: "var(--space-1)",
  fontSize: 12.5,
  color: "var(--ink-400)",
});

export const checkbox = style({
  display: "flex",
  alignItems: "center",
  gap: "var(--space-2)",
  fontSize: 13,
});
