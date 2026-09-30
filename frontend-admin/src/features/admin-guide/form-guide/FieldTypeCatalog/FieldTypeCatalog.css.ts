import { style } from "@vanilla-extract/css";

export const grid = style({
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
  gap: "var(--space-4)",
  "@media": { "(max-width: 767px)": { gridTemplateColumns: "minmax(0, 1fr)" } },
});

export const card = style({
  display: "grid",
  gap: "var(--space-3)",
  alignContent: "start",
  padding: "var(--space-4)",
  border: "1px solid var(--line)",
  borderRadius: "var(--r)",
  background: "var(--brand-25)",
});

export const name = style({ margin: 0, fontSize: 15.5, fontWeight: 700, color: "var(--ink-900)" });

export const use = style({ margin: 0, fontSize: 13.5, lineHeight: 1.55, color: "var(--ink-500)" });

export const preview = style({ justifySelf: "center", width: "100%", maxWidth: 340 });

export const help = style({ color: "var(--ink-400)", fontSize: 12 });
