import { style } from "@vanilla-extract/css";

import { fadeUp, reducedMotion } from "../../shared/motion.css";

export const rule = style({ display: "grid", gap: "var(--space-3)" });

export const ruleTitle = style({
  margin: 0,
  fontSize: 16,
  fontWeight: 700,
  color: "var(--ink-900)",
});

export const ruleText = style({
  margin: 0,
  color: "var(--ink-500)",
  fontSize: 14,
  lineHeight: 1.6,
  maxWidth: 760,
});

export const tapDemo = style({
  display: "grid",
  gap: "var(--space-2)",
  justifyItems: "center",
  width: "100%",
});

export const tapHint = style({ color: "var(--ink-400)", fontSize: 12.5, fontWeight: 600 });

export const back = style({
  justifySelf: "start",
  padding: 0,
  border: 0,
  background: "transparent",
  color: "#1b365d",
  font: "inherit",
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
});

export const pageEnter = style({
  display: "grid",
  gap: 10,
  animation: `${fadeUp} 300ms ease-out both`,
  "@media": { [reducedMotion]: { animation: "none" } },
});

export const bad = style({ textDecoration: "underline wavy #c83d3d", textUnderlineOffset: 4 });
