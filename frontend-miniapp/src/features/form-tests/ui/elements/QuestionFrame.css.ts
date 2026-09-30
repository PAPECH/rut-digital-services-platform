import { style } from "@vanilla-extract/css";

export const label = style({
  display: "block",
  fontSize: 15,
  fontWeight: 600,
  marginBottom: 8,
  lineHeight: 1.4,
});

export const required = style({
  color: "var(--st-rej-fg)",
});
