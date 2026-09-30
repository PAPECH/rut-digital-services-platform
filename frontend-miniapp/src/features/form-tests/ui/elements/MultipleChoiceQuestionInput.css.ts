import { style } from "@vanilla-extract/css";

export const list = style({
  display: "grid",
  gap: 8,
});

export const option = style({
  display: "flex",
  gap: 9,
  alignItems: "flex-start",
  fontSize: 15,
});

// Fixed px size, same reasoning as SingleChoiceQuestionInput.css.ts's `input`.
export const input = style({
  width: 18,
  height: 18,
  flexShrink: 0,
  marginTop: 1,
  accentColor: "var(--brand-500)",
});
