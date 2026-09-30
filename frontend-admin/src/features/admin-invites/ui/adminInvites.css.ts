import { style, styleVariants } from "@vanilla-extract/css";

export const section = style({
  display: "grid",
  gap: "var(--space-3)",
  marginTop: "var(--space-4)",
});

export const head = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  flexWrap: "wrap",
  gap: "var(--space-3)",
});

export const title = style({
  margin: 0,
  fontSize: 15,
});

export const list = style({
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
  gap: "var(--space-3)",
});

export const card = style({
  display: "grid",
  gap: "var(--space-2)",
  padding: "var(--space-3)",
  border: "1px solid var(--line)",
  borderRadius: 10,
  background: "#fff",
  minWidth: 0,
});

export const cardHead = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  gap: "var(--space-2)",
});

export const name = style({
  fontWeight: 600,
  overflowWrap: "anywhere",
});

export const meta = style({
  display: "grid",
  gap: 2,
  fontSize: 12,
  color: "var(--ink-400)",
});

export const badge = style({
  flexShrink: 0,
  padding: "2px 8px",
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 600,
});

export const badgeTone = styleVariants({
  active: { background: "var(--st-done-bg)", color: "var(--st-done-fg)" },
  expired: { background: "var(--ink-50)", color: "var(--ink-400)" },
  exhausted: { background: "var(--ink-50)", color: "var(--ink-400)" },
  revoked: { background: "var(--st-rej-bg)", color: "var(--st-rej-fg)" },
});

export const fieldRow = style({
  display: "grid",
  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
  gap: "var(--space-3)",
  "@media": {
    "(max-width: 640px)": { gridTemplateColumns: "1fr" },
  },
});

export const linkBox = style({
  display: "grid",
  gap: "var(--space-2)",
});

export const linkValue = style({
  padding: "var(--space-2) var(--space-3)",
  border: "1px solid var(--line)",
  borderRadius: 8,
  background: "var(--ink-50)",
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: 12,
  overflowWrap: "anywhere",
  userSelect: "all",
});

export const warning = style({
  margin: 0,
  fontSize: 12,
  color: "var(--ink-400)",
});
