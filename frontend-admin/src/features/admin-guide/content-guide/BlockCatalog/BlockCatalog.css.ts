import { style } from "@vanilla-extract/css";

export const group = style({ display: "grid", gap: "var(--space-3)" });

export const groupTitle = style({
  margin: "var(--space-2) 0 0",
  fontSize: 13,
  fontWeight: 700,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  color: "var(--ink-400)",
});

export const cards = style({
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
  gap: "var(--space-4)",
  "@media": { "(max-width: 767px)": { gridTemplateColumns: "minmax(0, 1fr)" } },
});
