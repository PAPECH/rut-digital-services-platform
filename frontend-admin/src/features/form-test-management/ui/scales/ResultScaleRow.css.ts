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
  flexWrap: "wrap",
});

export const identity = style({
  display: "flex",
  alignItems: "center",
  gap: "var(--space-3)",
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

export const meta = style({
  color: "var(--ink-400)",
  fontSize: 12,
});

export const actions = style({
  display: "flex",
  gap: "var(--space-2)",
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

export const row2 = style({
  display: "grid",
  gridTemplateColumns: "1fr 1fr",
  gap: "var(--space-3)",
});

export const termsHead = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  fontSize: 12.5,
  color: "var(--ink-400)",
  marginTop: "var(--space-1)",
});

export const termRow = style({
  display: "grid",
  gridTemplateColumns: "minmax(0, 1fr) 90px auto",
  gap: "var(--space-2)",
  alignItems: "center",
});

export const empty = style({
  fontSize: 12.5,
  color: "var(--ink-400)",
});
