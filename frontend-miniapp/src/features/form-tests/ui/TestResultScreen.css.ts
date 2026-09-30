import { style } from "@vanilla-extract/css";

export const wrap = style({
  textAlign: "center",
  padding: "48px 16px",
});

export const title = style({
  fontSize: 18,
  fontWeight: 700,
  marginBottom: 8,
});

export const message = style({
  fontSize: 14,
  color: "var(--ink-500)",
  marginBottom: 20,
});

export const resultText = style({
  fontSize: 14,
  color: "var(--ink-700, var(--ink-500))",
  marginBottom: 20,
  whiteSpace: "pre-wrap",
  textAlign: "left",
});

export const scores = style({
  textAlign: "left",
  background: "var(--surface-200, #f1f3f5)",
  borderRadius: 10,
  padding: "12px 14px",
  marginBottom: 20,
  display: "grid",
  gap: 6,
});

export const scoresLabel = style({
  fontSize: 12,
  fontWeight: 600,
  color: "var(--ink-400)",
});

export const scoreRow = style({
  display: "flex",
  justifyContent: "space-between",
  fontSize: 13.5,
});

export const scoreValue = style({
  fontWeight: 700,
});

export const errorBanner = style({
  margin: "0 0 16px",
  padding: "10px 12px",
  borderRadius: 10,
  background: "var(--st-rej-bg)",
  color: "var(--st-rej-fg)",
  fontSize: 13,
});

export const actions = style({
  display: "flex",
  flexDirection: "column",
  gap: 10,
  alignItems: "center",
});
