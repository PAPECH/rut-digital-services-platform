import { style } from "@vanilla-extract/css";

export const pageHead = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  flexWrap: "wrap",
  gap: "var(--space-3)",
  marginBottom: "var(--space-3)",
});

export const main = style({
  display: "grid",
  gap: "var(--space-4)",
});

export const errorBanner = style({
  color: "var(--danger-600, #b42318)",
  fontSize: 13,
  marginBottom: "var(--space-3)",
});

export const pickerTabsRow = style({
  display: "flex",
  alignItems: "center",
  flexWrap: "wrap",
  gap: "var(--space-3)",
});

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
  fontSize: 13,
  fontWeight: 600,
  cursor: "pointer",
  color: "var(--ink-700)",
});

export const tabActive = style([
  tab,
  {
    background: "var(--brand)",
    color: "#fff",
    borderColor: "var(--brand)",
    boxShadow: "var(--shadow-sm)",
  },
]);
