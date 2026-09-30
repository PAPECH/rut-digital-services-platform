import { style } from "@vanilla-extract/css";

import { fadeUp, reducedMotion, strike } from "../../shared/motion.css";

export const box = style({
  display: "grid",
  gridTemplateColumns: "minmax(0, 1fr) minmax(0, 360px)",
  gap: "var(--space-5)",
  alignItems: "center",
  padding: "var(--space-5)",
  borderLeft: "4px solid #e59b20",
  borderRadius: "var(--r)",
  background: "var(--st-work-bg)",
  "@media": { "(max-width: 900px)": { gridTemplateColumns: "minmax(0, 1fr)" } },
});

export const text = style({ display: "grid", gap: "var(--space-3)" });

export const title = style({
  margin: 0,
  fontSize: 17,
  fontWeight: 800,
  color: "var(--st-work-fg)",
});

export const paragraph = style({
  margin: 0,
  fontSize: 14,
  lineHeight: 1.6,
  color: "var(--ink-700)",
});

export const chips = style({ display: "flex", flexWrap: "wrap", gap: 6 });

export const chip = style({
  padding: "4px 10px",
  borderRadius: 999,
  background: "#fff",
  border: "1px solid #f0d49a",
  fontSize: 12.5,
  fontWeight: 600,
  color: "var(--ink-700)",
});

export const demo = style({ display: "grid", gap: "var(--space-3)", minWidth: 0 });

export const fields = style({ display: "grid", gap: "var(--space-2)" });

export const row = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 8,
  padding: "9px 12px",
  borderRadius: 8,
  background: "#fff",
  border: "1px solid var(--line)",
  fontSize: 13,
});

export const struck = style({
  color: "var(--ink-400)",
  backgroundImage: "linear-gradient(#c83d3d, #c83d3d)",
  backgroundRepeat: "no-repeat",
  backgroundPosition: "0 55%",
  backgroundSize: "100% 2px",
  animation: `${strike} 500ms ease-out both`,
  "@media": { [reducedMotion]: { animation: "none" } },
});

export const replacement = style({
  display: "grid",
  gap: 2,
  padding: "9px 12px",
  borderRadius: 8,
  background: "var(--st-done-bg)",
  color: "var(--st-done-fg)",
  fontSize: 13,
  animation: `${fadeUp} 380ms ease-out both`,
  "@media": { [reducedMotion]: { animation: "none" } },
});

export const tag = style({ fontSize: 11.5, fontWeight: 700, color: "var(--ink-400)" });
