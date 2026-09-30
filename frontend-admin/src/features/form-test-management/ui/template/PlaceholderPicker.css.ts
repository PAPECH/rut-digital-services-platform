import { style } from "@vanilla-extract/css";

export const wrapper = style({
  display: "grid",
  gap: "var(--space-2)",
  marginBottom: "var(--space-3)",
  padding: "var(--space-3)",
  border: "1px solid var(--line)",
  borderRadius: 10,
  background: "var(--surface-200, #f8f9fb)",
});

export const group = style({
  display: "flex",
  alignItems: "center",
  flexWrap: "wrap",
  gap: "var(--space-2)",
});

export const groupLabel = style({
  fontSize: 12.5,
  fontWeight: 600,
  color: "var(--ink-700)",
  minWidth: 120,
});

export const groupButtons = style({
  display: "flex",
  flexWrap: "wrap",
  gap: "var(--space-1)",
});

export const empty = style({
  fontSize: 12.5,
  color: "var(--ink-400)",
  margin: 0,
});
