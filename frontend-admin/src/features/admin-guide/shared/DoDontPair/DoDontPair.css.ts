import { style, styleVariants } from "@vanilla-extract/css";

export const pair = style({
  display: "grid",
  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
  gap: "var(--space-4)",
  "@media": { "(max-width: 767px)": { gridTemplateColumns: "1fr" } },
});

export const side = style({
  display: "grid",
  alignContent: "start",
  justifyItems: "center",
  gap: "var(--space-3)",
  padding: "var(--space-4)",
  borderRadius: "var(--r)",
  border: "1px solid",
});

export const sideTone = styleVariants({
  do: { borderColor: "#b7e4cc", background: "#f3fbf6" },
  dont: { borderColor: "#f1c4c4", background: "#fdf5f5" },
});

export const label = style({
  justifySelf: "start",
  padding: "3px 10px",
  borderRadius: 999,
  fontSize: 12,
  fontWeight: 700,
});

export const labelTone = styleVariants({
  do: { background: "var(--st-done-bg)", color: "var(--st-done-fg)" },
  dont: { background: "var(--st-rej-bg)", color: "var(--st-rej-fg)" },
});

export const caption = style({
  justifySelf: "stretch",
  margin: 0,
  color: "var(--ink-500)",
  fontSize: 13,
  lineHeight: 1.5,
});
