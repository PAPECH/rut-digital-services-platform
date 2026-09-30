import { style } from "@vanilla-extract/css";

export const tableWrap = style({
  overflow: "auto",
  maxHeight: "min(65vh, 720px)",
});

export const stickyHeadCell = style({
  position: "sticky",
  top: 0,
  zIndex: 1,
  background: "#fff",
  boxShadow: "inset 0 -1px 0 var(--line)",
});

export const emptyRow = style({
  textAlign: "center",
  padding: "var(--space-7)",
  color: "var(--ink-400)",
});
