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

// Fixed px size (not inherited from `option`'s font-size): iOS Safari sizes native
// radio/checkbox controls relative to the inherited font-size instead of the ~13px fixed size
// desktop browsers use, so without this they render inconsistently across questions with
// different surrounding font sizes (most visibly next to `ScaleQuestionMatrix`'s smaller table
// text) even though desktop looks fine either way.
export const input = style({
  width: 18,
  height: 18,
  flexShrink: 0,
  marginTop: 1,
  accentColor: "var(--brand-500)",
});
