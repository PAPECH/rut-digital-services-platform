import { style } from "@vanilla-extract/css";

export const badge = style({
  display: "inline-flex",
  justifySelf: "start",
  alignItems: "center",
  gap: 4,
  padding: "2px 8px",
  borderRadius: 999,
  background: "#fff4d6",
  border: "1px solid #f0d49a",
  color: "#8a5400",
  fontSize: 11,
  fontWeight: 700,
  whiteSpace: "nowrap",
});
