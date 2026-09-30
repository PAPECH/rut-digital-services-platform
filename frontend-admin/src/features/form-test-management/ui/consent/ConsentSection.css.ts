import { style } from "@vanilla-extract/css";

export const toggle = style({
  display: "flex",
  alignItems: "center",
  gap: "var(--space-2)",
  fontSize: 13.5,
  fontWeight: 600,
  marginBottom: "var(--space-3)",
  cursor: "pointer",
});

export const body = style({
  display: "grid",
  gap: "var(--space-3)",
});

export const field = style({
  display: "grid",
  gap: "var(--space-1)",
  fontSize: 12.5,
  color: "var(--ink-400)",
});

export const hint = style({
  fontSize: 12.5,
  color: "var(--ink-400)",
  margin: 0,
});

export const warning = style({
  fontSize: 12.5,
  color: "var(--warning-700, #b54708)",
  margin: 0,
});

export const preview = style({
  display: "grid",
  gap: "var(--space-1)",
  padding: "var(--space-3)",
  border: "1px dashed var(--line)",
  borderRadius: 10,
  background: "var(--surface-200, #f8f9fb)",
});

export const previewLabel = style({
  fontSize: 12,
  fontWeight: 600,
  color: "var(--ink-400)",
});

export const previewCheckbox = style({
  display: "flex",
  alignItems: "flex-start",
  gap: "var(--space-2)",
  fontSize: 13,
});

export const previewLink = style({
  color: "var(--brand-700, var(--brand-900))",
  textDecoration: "underline",
});
