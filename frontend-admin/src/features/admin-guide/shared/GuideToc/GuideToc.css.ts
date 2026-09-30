import { style } from "@vanilla-extract/css";

const mobile = "(max-width: 1023px)";

export const toc = style({
  position: "sticky",
  top: "var(--space-4)",
  alignSelf: "start",
  display: "grid",
  gap: 2,
  "@media": {
    [mobile]: {
      position: "static",
      display: "flex",
      gap: "var(--space-2)",
      overflowX: "auto",
      paddingBottom: "var(--space-1)",
      scrollbarWidth: "none",
    },
  },
});

export const link = style({
  display: "block",
  padding: "7px 12px",
  borderLeft: "2px solid var(--line)",
  color: "var(--ink-500)",
  fontSize: 13,
  fontWeight: 500,
  textDecoration: "none",
  transition: "color 200ms, border-color 200ms",
  ":hover": { color: "var(--brand)" },
  "@media": {
    [mobile]: {
      flex: "0 0 auto",
      padding: "6px 12px",
      border: "1px solid var(--line)",
      borderRadius: 999,
      background: "var(--card)",
      whiteSpace: "nowrap",
    },
  },
});

export const linkActive = style({
  borderColor: "var(--brand)",
  color: "var(--brand)",
  fontWeight: 700,
  "@media": { [mobile]: { background: "var(--brand-50)" } },
});
