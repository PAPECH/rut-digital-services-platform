import { style } from "@vanilla-extract/css";

export const photo = style({
  position: "relative",
  display: "block",
  width: "100%",
  height: "100%",
  minHeight: 32,
  overflow: "hidden",
  background: "linear-gradient(180deg, #bcd3ee 0%, #dfeaf7 55%, #cfe6d3 56%, #9ccaa5 100%)",
});

export const sun = style({
  position: "absolute",
  top: "16%",
  right: "18%",
  width: "18%",
  aspectRatio: "1",
  borderRadius: 999,
  background: "#fbe7a1",
});

export const hills = style({
  position: "absolute",
  inset: "auto 0 0 0",
  width: "100%",
  height: "58%",
});
