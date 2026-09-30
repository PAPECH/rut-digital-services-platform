import { style } from "@vanilla-extract/css";

export const header = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  gap: "var(--space-4)",
  marginBottom: "var(--space-4)",
});

export const title = style({
  fontSize: 16,
  fontWeight: 700,
});

export const subtitle = style({
  fontSize: 12.5,
  color: "var(--ink-400)",
  marginTop: "var(--space-1)",
});

export const statsGrid = style({
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
  gap: "var(--space-3)",
  marginBottom: "var(--space-4)",
});

export const statCard = style({
  border: "1px solid var(--line)",
  borderRadius: 8,
  padding: "var(--space-3)",
});

export const statValue = style({
  fontSize: 20,
  fontWeight: 700,
});

export const statLabel = style({
  fontSize: 12,
  color: "var(--ink-400)",
});

export const scaleList = style({
  display: "grid",
  gap: "var(--space-2)",
});

export const scaleRow = style({
  display: "flex",
  justifyContent: "space-between",
  fontSize: 13,
  padding: "var(--space-2) 0",
  borderBottom: "1px solid var(--line)",
});

export const scaleName = style({
  color: "var(--ink-700)",
});

export const scaleMeta = style({
  color: "var(--ink-400)",
  fontSize: 12,
});

export const empty = style({
  color: "var(--ink-400)",
  fontSize: 13,
  padding: "var(--space-6)",
  textAlign: "center",
});
