import { style } from "@vanilla-extract/css";

export const list = style({
  display: "flex",
  flexDirection: "column",
  gap: 14,
});

export const divider = style({
  border: "none",
  borderTop: "1px solid var(--line)",
  margin: 0,
});

export const errorBanner = style({
  margin: "16px 0",
  padding: "10px 12px",
  borderRadius: 10,
  background: "var(--st-rej-bg)",
  color: "var(--st-rej-fg)",
  fontSize: 13,
});

export const footer = style({
  marginTop: 18,
  display: "flex",
  alignItems: "center",
  gap: 10,
});

export const consentRow = style({
  display: "flex",
  alignItems: "flex-start",
  gap: 10,
  marginTop: 18,
  padding: "12px 14px",
  borderRadius: 10,
  background: "var(--surface-200, #f1f3f5)",
  fontSize: 13.5,
  lineHeight: 1.4,
});

export const consentCheckbox = style({
  marginTop: 2,
  flexShrink: 0,
});

export const consentLink = style({
  background: "none",
  border: "none",
  padding: 0,
  font: "inherit",
  color: "var(--brand-700, var(--brand-900))",
  textDecoration: "underline",
  cursor: "pointer",
});

export const autosaveHint = style({
  fontSize: 12,
  color: "var(--ink-400)",
});
