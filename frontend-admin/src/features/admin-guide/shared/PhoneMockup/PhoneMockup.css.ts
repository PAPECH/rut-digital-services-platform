import { style } from "@vanilla-extract/css";

export const frame = style({
  width: "100%",
  maxWidth: 340,
  border: "1px solid var(--line-strong)",
  borderRadius: 26,
  background: "#f7f8fb",
  boxShadow: "var(--shadow)",
  overflow: "hidden",
});

export const bar = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "8px 16px",
  background: "#fff",
  borderBottom: "1px solid var(--line)",
  color: "var(--ink-400)",
  fontSize: 11,
  fontWeight: 600,
});

export const screen = style({
  display: "grid",
  alignContent: "start",
  gap: 10,
  padding: 14,
  minHeight: 120,
  fontSize: 13.5,
  fontFamily: "'Inter', var(--font)",
});
