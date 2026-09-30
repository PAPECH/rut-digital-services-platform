import { style } from "@vanilla-extract/css";

export const overlay = style({
  position: "fixed",
  inset: 0,
  zIndex: 50,
  display: "flex",
  justifyContent: "flex-end",
});

export const backdrop = style({
  position: "absolute",
  inset: 0,
  background: "rgba(11,23,41,.32)",
});

export const panel = style({
  position: "relative",
  width: 520,
  maxWidth: "100vw",
  height: "100%",
  background: "#fff",
  borderLeft: "1px solid var(--line)",
  boxShadow: "var(--shadow-lg)",
  display: "flex",
  flexDirection: "column",
});

export const head = style({
  padding: "var(--space-5) var(--space-6)",
  borderBottom: "1px solid var(--line)",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
});

export const headTitle = style({
  fontSize: 16,
  fontWeight: 700,
});

export const headSubtitle = style({
  fontSize: 12.5,
  color: "var(--ink-400)",
});

export const body = style({
  padding: "var(--space-4) var(--space-6)",
  overflow: "auto",
});

export const sectionTitle = style({
  fontSize: 12,
  color: "var(--ink-500)",
  textTransform: "uppercase",
  letterSpacing: ".06em",
  marginTop: "var(--space-6)",
  marginBottom: "var(--space-2)",
});

export const scaleRow = style({
  display: "flex",
  justifyContent: "space-between",
  padding: "var(--space-2) 0",
  borderBottom: "1px solid var(--line)",
  fontSize: 13,
});

export const scaleLabel = style({
  color: "var(--ink-700)",
});

export const scaleValue = style({
  display: "flex",
  flexDirection: "column",
  alignItems: "flex-end",
  gap: "var(--space-1)",
});

export const flaggedTag = style({
  marginLeft: "var(--space-2)",
});

export const scaleValueMeta = style({
  color: "var(--ink-400)",
  fontSize: 12,
});

export const answerRow = style({
  display: "flex",
  justifyContent: "space-between",
  gap: "var(--space-3)",
  padding: "var(--space-2) 0",
  borderBottom: "1px solid var(--line)",
  fontSize: 13,
});

export const answerLabel = style({
  color: "var(--ink-500)",
});

export const resultText = style({
  whiteSpace: "pre-wrap",
  fontSize: 13,
  background: "var(--brand-50)",
  borderRadius: 8,
  padding: "var(--space-3)",
});

export const loadingState = style({
  padding: "var(--space-7)",
  textAlign: "center",
  color: "var(--ink-400)",
});
