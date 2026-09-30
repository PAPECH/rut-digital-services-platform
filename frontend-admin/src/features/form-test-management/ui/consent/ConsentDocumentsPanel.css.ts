import { style } from "@vanilla-extract/css";

export const header = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "var(--space-3)",
  marginBottom: "var(--space-2)",
});

export const title = style({
  fontSize: 16,
  fontWeight: 700,
  margin: 0,
});

export const hint = style({
  fontSize: 12.5,
  color: "var(--ink-400)",
  marginBottom: "var(--space-3)",
});

export const errorBanner = style({
  color: "var(--danger-600, #b42318)",
  fontSize: 13,
  marginBottom: "var(--space-3)",
});

export const editor = style({
  display: "grid",
  gap: "var(--space-3)",
  padding: "var(--space-3)",
  border: "1px solid var(--line)",
  borderRadius: 10,
  background: "var(--surface-200, #f8f9fb)",
  marginBottom: "var(--space-3)",
});

export const field = style({
  display: "grid",
  gap: "var(--space-1)",
  fontSize: 12.5,
  color: "var(--ink-400)",
});

export const editorActions = style({
  display: "flex",
  justifyContent: "flex-end",
  gap: "var(--space-2)",
});

export const list = style({
  display: "grid",
  gap: "var(--space-2)",
  margin: 0,
  padding: 0,
  listStyle: "none",
});

export const row = style({
  display: "flex",
  alignItems: "center",
  gap: "var(--space-3)",
  padding: "var(--space-2) var(--space-3)",
  border: "1px solid var(--line)",
  borderRadius: 8,
  flexWrap: "wrap",
});

export const rowTitle = style({
  fontWeight: 600,
  fontSize: 13.5,
  flex: "1 1 auto",
});

export const rowMeta = style({
  fontSize: 12,
  color: "var(--ink-400)",
});

export const rowActions = style({
  display: "flex",
  gap: "var(--space-1)",
});
