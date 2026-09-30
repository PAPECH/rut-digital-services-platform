import { style } from "@vanilla-extract/css";

export const toolbar = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  gap: "var(--space-3)",
  flexWrap: "wrap",
  marginBottom: "var(--space-3)",
});

export const title = style({
  fontSize: 16,
  fontWeight: 700,
  margin: 0,
});

export const meta = style({
  fontSize: 12,
  color: "var(--ink-400)",
});

export const actions = style({
  display: "flex",
  gap: "var(--space-2)",
  flexWrap: "wrap",
});

export const hiddenInput = style({
  display: "none",
});

export const errorBanner = style({
  color: "var(--danger-600, #b42318)",
  fontSize: 13,
  marginBottom: "var(--space-3)",
});

export const noticeBanner = style({
  color: "var(--success-600, #087443)",
  fontSize: 13,
  marginBottom: "var(--space-3)",
});

export const metaFields = style({
  display: "grid",
  gap: "var(--space-3)",
  marginBottom: "var(--space-4)",
});

export const field = style({
  display: "grid",
  gap: "var(--space-1)",
  fontSize: 12.5,
  color: "var(--ink-400)",
});

export const mobileNotice = style({
  display: "none",
  fontSize: 12.5,
  color: "var(--ink-400)",
  background: "var(--surface-200, #f1f3f5)",
  borderRadius: 8,
  padding: "var(--space-2) var(--space-3)",
  marginBottom: "var(--space-3)",
  "@media": {
    "screen and (max-width: 640px)": {
      display: "block",
    },
  },
});

export const section = style({
  marginTop: "var(--space-5)",
  paddingTop: "var(--space-4)",
  borderTop: "1px solid var(--line)",
});
