import { style } from "@vanilla-extract/css";

export const root = style({ display: "grid", gap: "var(--space-3)" });

export const list = style({ display: "grid", gap: 6, margin: 0, padding: 0, listStyle: "none" });

export const listInline = style({
  display: "flex",
  margin: 0,
  padding: 0,
  listStyle: "none",
  flexWrap: "wrap",
  gap: "var(--space-2)",
});

export const item = style({
  display: "grid",
  gridTemplateColumns: "26px 1fr",
  gap: "var(--space-2)",
  alignItems: "start",
  width: "100%",
  padding: "8px 10px",
  border: "1px solid transparent",
  borderRadius: 8,
  background: "transparent",
  color: "var(--ink-500)",
  font: "inherit",
  fontSize: 13.5,
  lineHeight: 1.5,
  textAlign: "left",
  cursor: "pointer",
  transition: "background 200ms, border-color 200ms, color 200ms",
  ":hover": { background: "var(--ink-50)" },
});

export const itemInline = style({
  display: "inline-flex",
  width: "auto",
  alignItems: "center",
  padding: "5px 12px 5px 6px",
  borderColor: "var(--line)",
  borderRadius: 999,
  background: "var(--card)",
  fontWeight: 600,
});

export const itemActive = style({
  borderColor: "var(--brand-500)",
  background: "var(--brand-50)",
  color: "var(--ink-900)",
  ":hover": { background: "var(--brand-50)" },
});

export const itemDone = style({ color: "var(--ink-700)" });

export const number = style({
  display: "grid",
  width: 24,
  height: 24,
  placeItems: "center",
  borderRadius: 999,
  background: "var(--ink-100)",
  color: "var(--ink-500)",
  fontSize: 12,
  fontWeight: 700,
  selectors: {
    [`${itemActive} &`]: { background: "var(--brand)", color: "#fff" },
    [`${itemDone} &`]: { background: "var(--st-done-bg)", color: "var(--st-done-fg)" },
  },
});

export const itemTitle = style({ display: "block", fontWeight: 700, color: "var(--ink-900)" });

export const controls = style({
  display: "flex",
  flexWrap: "wrap",
  alignItems: "center",
  gap: "var(--space-2)",
});

export const counter = style({ marginLeft: "auto", color: "var(--ink-400)", fontSize: 12.5 });

export const current = style({
  margin: 0,
  padding: "var(--space-3) var(--space-4)",
  borderLeft: "4px solid var(--brand-500)",
  borderRadius: 8,
  background: "var(--brand-50)",
  color: "var(--ink-700)",
  fontSize: 14,
  lineHeight: 1.55,
});
