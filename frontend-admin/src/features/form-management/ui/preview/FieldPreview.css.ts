import { style } from "@vanilla-extract/css";

/** Mirrors the mini-app's field inputs (`frontend-miniapp/src/features/forms/ui/fields`). */
export const fieldset = style({ margin: 0, padding: 0, border: 0, minWidth: 0 });

export const choiceList = style({ display: "grid", gap: 8 });

export const choice = style({
  display: "flex",
  alignItems: "center",
  gap: 9,
  color: "var(--ink-900)",
  fontSize: 14,
  fontWeight: 400,
});

export const checkboxRow = style({
  display: "flex",
  alignItems: "flex-start",
  gap: 10,
  color: "var(--ink-900)",
  fontSize: 14,
  fontWeight: 400,
});

export const control = style({ flex: "none", margin: "2px 0 0" });

export const required = style({ color: "var(--st-rej-fg)" });

export const fileInput = style({
  display: "flex",
  alignItems: "center",
  gap: 10,
  opacity: 0.8,
});

export const fileButton = style({
  flexShrink: 0,
  padding: "6px 14px",
  border: "1px solid var(--line)",
  borderRadius: 8,
  background: "var(--ink-50)",
  fontSize: 14,
  fontWeight: 500,
});

export const fileName = style({ color: "var(--ink-400)", fontSize: 14 });

export const fileLimits = style({ display: "block", marginTop: 5, color: "var(--ink-400)", fontSize: 12 });
