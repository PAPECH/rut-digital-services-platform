import { style } from "@vanilla-extract/css";

export const layout = style({
  display: "grid",
  gridTemplateColumns: "200px minmax(0, 1fr)",
  gap: "var(--space-6)",
  alignItems: "start",
  "@media": {
    "(max-width: 1023px)": { gridTemplateColumns: "minmax(0, 1fr)", gap: "var(--space-3)" },
  },
});

export const body = style({
  display: "grid",
  gap: "var(--space-5)",
  minWidth: 0,
});
