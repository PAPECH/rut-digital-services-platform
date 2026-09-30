import { style } from "@vanilla-extract/css";

export const notes = style({
  display: "grid",
  gap: "var(--space-2)",
  margin: 0,
  paddingLeft: 20,
  color: "var(--ink-700)",
  fontSize: 14,
  lineHeight: 1.6,
});
