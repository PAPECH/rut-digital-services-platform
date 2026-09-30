import { style } from "@vanilla-extract/css";

export const hint = style({
  display: "grid",
  gridTemplateColumns: "auto minmax(0, 1fr) auto",
  alignItems: "start",
  gap: "var(--space-4)",
  marginBottom: "var(--space-5)",
  padding: "var(--space-4) var(--space-5)",
  border: "1px solid #f0d49a",
  borderRadius: "var(--r-lg)",
  background: "#fffaf0",
  "@media": {
    "(max-width: 767px)": { gridTemplateColumns: "minmax(0, 1fr)", gap: "var(--space-3)" },
  },
});

export const icon = style({
  fontSize: 26,
  lineHeight: 1,
  "@media": { "(max-width: 767px)": { display: "none" } },
});

export const content = style({ display: "grid", gap: "var(--space-2)" });

export const title = style({ margin: 0, fontSize: 15, fontWeight: 800, color: "var(--ink-900)" });

export const list = style({
  display: "grid",
  gap: 6,
  margin: 0,
  padding: 0,
  listStyle: "none",
  color: "var(--ink-700)",
  fontSize: 13.5,
  lineHeight: 1.5,
});

export const row = style({
  display: "grid",
  gridTemplateColumns: "150px minmax(0, 1fr)",
  alignItems: "center",
  gap: "var(--space-3)",
  "@media": { "(max-width: 767px)": { gridTemplateColumns: "minmax(0, 1fr)", gap: 4 } },
});

export const ringSample = style({
  justifySelf: "start",
  padding: "3px 10px",
  borderRadius: 6,
  background: "#fff",
  fontSize: 12,
  fontWeight: 600,
});

export const staticSample = style({
  justifySelf: "start",
  padding: "3px 10px",
  border: "1px dashed var(--ink-300)",
  borderRadius: 6,
  color: "var(--ink-400)",
  fontSize: 12,
  fontWeight: 600,
});
