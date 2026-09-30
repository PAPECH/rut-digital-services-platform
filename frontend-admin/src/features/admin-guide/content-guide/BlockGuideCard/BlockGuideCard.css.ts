import { style } from "@vanilla-extract/css";

export const card = style({
  display: "grid",
  gap: "var(--space-3)",
  alignContent: "start",
  padding: "var(--space-4)",
  border: "1px solid var(--line)",
  borderRadius: "var(--r)",
  background: "var(--brand-25)",
});

export const name = style({ margin: 0, fontSize: 16, fontWeight: 700, color: "var(--ink-900)" });

export const purpose = style({
  margin: 0,
  fontSize: 13.5,
  lineHeight: 1.55,
  color: "var(--ink-700)",
});

export const rules = style({ display: "grid", gap: 6, margin: 0, padding: 0, listStyle: "none" });

export const rule = style({
  display: "grid",
  gridTemplateColumns: "18px 1fr",
  gap: 6,
  fontSize: 13,
  lineHeight: 1.5,
  color: "var(--ink-500)",
});

export const ruleDo = style({ color: "var(--st-done-fg)", fontWeight: 800 });

export const ruleDont = style({ color: "var(--st-rej-fg)", fontWeight: 800 });

export const example = style({
  display: "grid",
  gap: 6,
  justifySelf: "center",
  width: "100%",
  maxWidth: 340,
});

export const caption = style({ fontSize: 12, fontWeight: 700, color: "var(--ink-500)" });
