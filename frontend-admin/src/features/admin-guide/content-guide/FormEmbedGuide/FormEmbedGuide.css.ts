import { style } from "@vanilla-extract/css";

import { fadeUp, reducedMotion } from "../../shared/motion.css";

export const layout = style({
  display: "grid",
  gridTemplateColumns: "minmax(0, 1fr) minmax(0, 390px)",
  gap: "var(--space-6)",
  alignItems: "start",
  "@media": { "(max-width: 900px)": { gridTemplateColumns: "minmax(0, 1fr)" } },
});

export const blockEnter = style({
  display: "grid",
  gap: 10,
  borderRadius: 22,
  animation: `${fadeUp} 300ms ease-out both`,
  "@media": { [reducedMotion]: { animation: "none" } },
});

export const placeholder = style({
  padding: 18,
  border: "1.5px dashed #c9d0dd",
  borderRadius: 22,
  color: "#98a2b8",
  fontSize: 13,
  textAlign: "center",
});
