import { style } from "@vanilla-extract/css";

export const viewer = style({
  position: "relative",
  display: "grid",
  gap: 10,
  padding: 12,
  borderRadius: 14,
  background: "rgba(11, 23, 41, 0.88)",
  color: "#fff",
});

export const viewerHead = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 8,
  fontSize: 12.5,
  fontWeight: 600,
});

export const viewerClose = style({
  padding: "2px 8px",
  border: 0,
  borderRadius: 999,
  background: "rgba(255,255,255,0.15)",
  color: "#fff",
  cursor: "pointer",
});

export const viewerImage = style({ height: 150, borderRadius: 10, overflow: "hidden" });

export const inlineImage = style({ height: 150 });

export const hint = style({ color: "#6b7891", fontSize: 11.5, textAlign: "center" });
