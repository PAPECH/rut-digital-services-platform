import { style } from "@vanilla-extract/css";

export const scroll = style({
  overflowX: "auto",
  margin: "0 -16px",
  padding: "0 16px",
});

export const table = style({
  borderCollapse: "collapse",
  width: "100%",
  fontSize: 13.5,
});

export const statementCell = style({
  textAlign: "left",
  padding: "8px 10px 8px 0",
  minWidth: 180,
  maxWidth: 260,
  lineHeight: 1.35,
  borderBottom: "1px solid var(--line)",
});

export const optionHeaderCell = style({
  padding: "0 6px 8px",
  fontWeight: 500,
  color: "var(--ink-500)",
  textAlign: "center",
  minWidth: 56,
  verticalAlign: "bottom",
});

export const optionCell = style({
  padding: "8px 6px",
  textAlign: "center",
  borderBottom: "1px solid var(--line)",
});

// Fixed px size, not inherited from the table's small font-size: this is the specific input
// iOS Safari rendered inconsistently, since it scales native radio controls with the inherited
// font-size (desktop browsers don't) -- same fix as Single/MultipleChoiceQuestionInput.css.ts.
export const input = style({
  width: 18,
  height: 18,
  accentColor: "var(--brand-500)",
});
