import { style } from "@vanilla-extract/css";

import { fadeUp, reducedMotion } from "../../shared/motion.css";

export const layout = style({ display: "grid", gap: "var(--space-4)", minWidth: 0 });

export const stageGrid = style({
  display: "grid",
  gridTemplateColumns: "minmax(0, 1fr) minmax(0, 340px)",
  gap: "var(--space-5)",
  alignItems: "start",
  "@media": { "(max-width: 900px)": { gridTemplateColumns: "minmax(0, 1fr)" } },
});

export const builder = style({
  display: "grid",
  gap: "var(--space-3)",
  padding: "var(--space-4)",
  border: "1px solid var(--line)",
  borderRadius: "var(--r)",
  alignContent: "start",
  background: "var(--card)",
  minHeight: 220,
});

export const builderRow = style({
  display: "grid",
  gap: "var(--space-2)",
  padding: "var(--space-3)",
  border: "1px solid var(--line)",
  borderRadius: 8,
  background: "var(--brand-25)",
  animation: `${fadeUp} 360ms ease-out both`,
  "@media": { [reducedMotion]: { animation: "none" } },
});

export const fakeControl = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 8,
  padding: "7px 10px",
  border: "1px solid var(--line-strong)",
  borderRadius: 8,
  background: "#fff",
  fontSize: 13,
  color: "var(--ink-900)",
});

export const fieldLabel = style({ fontSize: 11.5, fontWeight: 600, color: "var(--ink-500)" });

export const toggle = style({ display: "flex", alignItems: "center", gap: 8, fontSize: 13 });

export const toggleBox = style({
  display: "grid",
  width: 16,
  height: 16,
  placeItems: "center",
  border: "1.5px solid var(--ink-300)",
  borderRadius: 4,
  color: "#fff",
  fontSize: 11,
  transition: "background 200ms, border-color 200ms",
});

export const toggleBoxOn = style({ background: "var(--brand)", borderColor: "var(--brand)" });

export const options = style({
  display: "flex",
  flexWrap: "wrap",
  gap: 6,
  padding: 4,
  borderRadius: 8,
});

export const option = style({
  padding: "3px 10px",
  borderRadius: 999,
  background: "var(--ink-50)",
  fontSize: 12.5,
  animation: `${fadeUp} 300ms ease-out both`,
  "@media": { [reducedMotion]: { animation: "none" } },
});

export const actions = style({
  display: "flex",
  gap: "var(--space-2)",
  flexWrap: "wrap",
  justifySelf: "start",
  padding: 4,
  borderRadius: 10,
});

export const empty = style({ color: "#98a2b8", fontSize: 13 });

export const formTitle = style({ margin: 0, fontSize: 17, fontWeight: 700, color: "#1b365d" });
