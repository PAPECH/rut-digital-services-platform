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

export const ruleRow = style({
  display: "grid",
  gap: "var(--space-2)",
});

export const ruleGrid = style({
  display: "grid",
  gridTemplateColumns: "90px 90px minmax(0, 1fr) auto auto",
  gap: "var(--space-2)",
  alignItems: "center",
});

export const flagLabel = style({
  display: "flex",
  alignItems: "center",
  gap: "var(--space-1)",
  fontSize: 12.5,
  whiteSpace: "nowrap",
});
