import { style, styleVariants } from "@vanilla-extract/css";

export const stage = style({
  display: "grid",
  gridTemplateColumns: "minmax(0, 1fr) auto minmax(0, 340px)",
  alignItems: "start",
  gap: "var(--space-5)",
  "@media": {
    "(max-width: 900px)": { gridTemplateColumns: "minmax(0, 1fr)", justifyItems: "stretch" },
  },
});

export const editor = style({
  display: "grid",
  gap: "var(--space-3)",
  padding: "var(--space-4)",
  border: "1px solid var(--line-strong)",
  borderRadius: "var(--r)",
  background: "var(--card)",
  boxShadow: "var(--shadow-sm)",
});

export const editorLabel = style({ fontSize: 12, fontWeight: 600, color: "var(--ink-500)" });

export const fakeInput = style({
  padding: "9px 11px",
  border: "1px solid var(--line-strong)",
  borderRadius: 8,
  background: "#fff",
  fontSize: 13.5,
  color: "var(--ink-900)",
  minHeight: 38,
});

export const actions = style({ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" });

export const status = style({
  justifySelf: "start",
  padding: "3px 10px",
  borderRadius: 999,
  fontSize: 12,
  fontWeight: 600,
  transition: "background 300ms, color 300ms",
});

export const statusTone = styleVariants({
  dirty: { background: "var(--ink-50)", color: "var(--ink-500)" },
  saved: { background: "var(--st-work-bg)", color: "var(--st-work-fg)" },
  published: { background: "var(--st-done-bg)", color: "var(--st-done-fg)" },
});

export const arrow = style({
  alignSelf: "center",
  color: "var(--ink-300)",
  fontSize: 26,
  "@media": { "(max-width: 900px)": { display: "none" } },
});
