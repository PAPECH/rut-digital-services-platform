import { style } from "@vanilla-extract/css";

export const head = style({
  display: "grid",
  gap: "var(--space-3)",
  marginBottom: "var(--space-5)",
});

export const subtitle = style({ margin: 0, color: "var(--ink-500)", fontSize: 14 });

export const tabs = style({
  display: "flex",
  gap: "var(--space-2)",
  flexWrap: "wrap",
});

export const tab = style({
  padding: "var(--space-2) var(--space-4)",
  borderRadius: 8,
  border: "1px solid var(--line)",
  background: "#fff",
  fontSize: 14,
  fontWeight: 600,
  cursor: "pointer",
  color: "var(--ink-700)",
});

export const tabActive = style([
  tab,
  { background: "var(--brand)", borderColor: "var(--brand)", color: "#fff" },
]);
