import { style } from "@vanilla-extract/css";

/** Tinted, framed area that visibly separates a demonstration from the instruction text. */
export const stage = style({
  display: "grid",
  gap: 0,
  overflow: "hidden",
  border: "1px solid #cfd8e6",
  borderRadius: "var(--r-lg)",
  background: "#e9eef6",
  boxShadow: "inset 0 1px 3px rgba(11, 23, 41, 0.06)",
  minWidth: 0,
});

export const header = style({
  display: "flex",
  alignItems: "center",
  gap: "var(--space-2)",
  padding: "8px var(--space-4)",
  borderBottom: "1px solid #cfd8e6",
  background: "#dde5f0",
});

export const title = style({
  color: "var(--brand)",
  fontSize: 12,
  fontWeight: 800,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
});

export const body = style({
  padding: "var(--space-5)",
  minWidth: 0,
  "@media": { "(max-width: 767px)": { padding: "var(--space-3)" } },
});
