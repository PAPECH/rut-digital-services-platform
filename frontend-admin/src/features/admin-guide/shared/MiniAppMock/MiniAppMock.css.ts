import { style, styleVariants } from "@vanilla-extract/css";

/**
 * Admin-side copies of the mini-app look, used only by guide mockups. Values mirror
 * `frontend-miniapp/src/styles/globals.css` (`.cms-*`, `.card`, `.service-form-card`,
 * `.sub-card`, `.tag`, `.faq-*`, `.news-card*`, `.section-label`). When the mini-app's visuals
 * change, update this file in the same change (see guardrails «Admin guide»).
 */
const brand = "#1b365d";
const brand500 = "#3e6baa";
const brand100 = "#dce5f0";
const brand50 = "#eef2f8";
const brand25 = "#f5f7fb";
const ink900 = "#0b1729";
const ink700 = "#1b2540";
const ink500 = "#4a5773";
const ink400 = "#6b7891";
const ink300 = "#98a2b8";
const ink50 = "#f2f4f8";
const line = "#e7eaf1";

// ── Text ────────────────────────────────────────────────────────────────────────────────────
const headingBase = { margin: "6px 0 0", color: brand, letterSpacing: "-0.015em" } as const;

export const heading = styleVariants({
  1: { ...headingBase, fontSize: 32, fontWeight: 600 },
  2: { ...headingBase, fontSize: 24, fontWeight: 600 },
  3: { ...headingBase, fontSize: 18, fontWeight: 500 },
  4: { ...headingBase, fontSize: 16, fontWeight: 400 },
  5: { ...headingBase, fontSize: 14, fontWeight: 300 },
  6: { ...headingBase, fontSize: 12, fontWeight: 200 },
});

export const paragraph = style({ margin: 0, color: ink700, fontSize: 13.5, lineHeight: 1.6 });

export const list = style([paragraph, { display: "grid", gap: 2, paddingLeft: 20 }]);

export const callout = style({
  padding: "13px 14px",
  borderLeft: `4px solid ${brand500}`,
  borderRadius: 11,
  background: brand50,
  color: ink700,
  fontSize: 13.5,
  lineHeight: 1.6,
});

export const calloutTone = styleVariants({
  info: {},
  warning: { borderColor: "#e59b20", background: "#fff1d6" },
  success: { borderColor: "#16835b", background: "#d9f4e5" },
  danger: { borderColor: "#c83d3d", background: "#fce4e4" },
});

export const calloutTitle = style({ display: "block", marginBottom: 4, fontSize: 13 });

export const sectionLabel = style({
  margin: "6px 0 0",
  color: ink500,
  fontSize: 13,
  fontWeight: 600,
  letterSpacing: "0.06em",
  textTransform: "uppercase",
});

// ── Category card (`.cms-category-card`) ────────────────────────────────────────────────────
export const tile = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
  width: "100%",
  minHeight: 76,
  padding: 16,
  border: `1px solid ${line}`,
  borderRadius: 16,
  background: "#fff",
  color: ink900,
  font: "inherit",
  textAlign: "left",
  boxShadow: "0 1px 0 rgba(11,23,41,0.04), 0 1px 2px rgba(11,23,41,0.04)",
  transition: "transform 150ms",
});

export const tileClickable = style({ cursor: "pointer", ":active": { transform: "scale(0.985)" } });

export const tileFilled = style({ borderColor: brand, background: brand, color: "#fff" });

export const tileText = style({ display: "flex", flexDirection: "column", gap: 8, minWidth: 0 });

export const tileTitle = style({ fontSize: 17, fontWeight: 600 });

export const tileSubtitle = style({
  color: ink400,
  fontSize: 14,
  lineHeight: 1.35,
  selectors: { [`${tileFilled} &`]: { color: "#fff", opacity: 0.8 } },
});

export const tileIcon = style({
  display: "grid",
  flex: "0 0 64px",
  width: 64,
  height: 64,
  placeItems: "center",
  overflow: "hidden",
  borderRadius: 12,
  background: brand50,
  color: brand,
  fontSize: 22,
  selectors: { [`${tileFilled} &`]: { background: "rgba(255,255,255,0.15)", color: "#fff" } },
});

export const grid = style({ display: "grid", gap: 9 });

// ── Action cards (`.card.service-form-card.cms-form-action`) ────────────────────────────────
export const actionCard = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
  padding: 18,
  border: `1px solid ${brand100}`,
  borderRadius: 22,
  background: `linear-gradient(135deg, #fff, ${brand25})`,
  color: ink900,
});

export const actionText = style({ display: "grid", gap: 3, minWidth: 0 });

export const actionTitle = style({ fontSize: 15, fontWeight: 700 });

export const actionDescription = style({ color: ink400, fontSize: 12.5 });

export const actionChevron = style({ color: brand, fontSize: 22, lineHeight: 1 });

// ── Submission / attempt card (`.sub-card` + `.tag`) ────────────────────────────────────────
export const subCard = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  gap: 12,
  padding: 16,
  borderRadius: 14,
  background: "#fff",
});

export const subName = style({ color: "#26303b", fontSize: 17, fontWeight: 700, lineHeight: 1.2 });

export const subMeta = style({ marginTop: 2, color: "#7b8491", fontSize: 12 });

export const tag = style({
  display: "inline-flex",
  alignItems: "center",
  gap: 6,
  flex: "none",
  padding: "4px 10px",
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 500,
  lineHeight: 1.1,
});

export const tagDot = style({ width: 6, height: 6, borderRadius: 999, background: "currentColor" });

export const tagTone = styleVariants({
  new: { background: "#dceaff", color: "#2d68bd" },
  work: { background: "#f4f0bd", color: "#80751b" },
  done: { background: "#c9f2c8", color: "#2c7a35" },
});

// ── Accordion / FAQ (`.faq-item`) ───────────────────────────────────────────────────────────
export const faqItem = style({
  padding: 14,
  border: `1px solid ${line}`,
  borderRadius: 16,
  background: "#fff",
});

export const faqQuestion = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 8,
  width: "100%",
  padding: 0,
  border: 0,
  background: "transparent",
  color: ink900,
  font: "inherit",
  fontSize: 14,
  fontWeight: 600,
  textAlign: "left",
  cursor: "pointer",
});

export const faqChevron = style({ color: ink400, transition: "transform 150ms" });

export const faqChevronOpen = style({ transform: "rotate(180deg)" });

export const faqAnswer = style({
  marginTop: 10,
  paddingTop: 10,
  borderTop: `1px solid ${line}`,
  color: ink700,
  fontSize: 13.5,
  lineHeight: 1.5,
});

// ── Steps (`.cms-steps`) ────────────────────────────────────────────────────────────────────
export const steps = style({ display: "grid", gap: 12, margin: 0, padding: 0, listStyle: "none" });

export const stepRow = style({
  display: "grid",
  gridTemplateColumns: "auto minmax(0, 1fr)",
  gap: 11,
});

export const stepNumber = style({
  display: "grid",
  width: 29,
  height: 29,
  placeItems: "center",
  borderRadius: 999,
  background: brand,
  color: "#fff",
  fontSize: 11,
  fontWeight: 800,
});

export const stepTitle = style({
  display: "block",
  marginBottom: 3,
  fontSize: 13,
  fontWeight: 700,
});

// ── Tabs (`.cms-tabs__list`) ────────────────────────────────────────────────────────────────
export const tabs = style({
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
  gap: 8,
});

export const tab = style({
  padding: "10px 16px",
  border: 0,
  borderRadius: 999,
  background: ink50,
  color: ink500,
  font: "inherit",
  fontSize: 13,
  fontWeight: 700,
  cursor: "pointer",
  transition: "background 200ms, color 200ms",
});

export const tabActive = style({ background: brand, color: "#fff" });

// ── Contacts (`.cms-contacts`) ──────────────────────────────────────────────────────────────
export const contactRow = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
  padding: "12px 13px",
  border: `1px solid ${line}`,
  borderRadius: 11,
  background: "#fff",
});

export const contactLabel = style({ color: ink400, fontSize: 11 });

export const contactValue = style({ fontSize: 12.5, fontWeight: 700, textAlign: "right" });

export const contactLink = style([contactValue, { color: brand }]);

// ── Link (`.cms-link`) ──────────────────────────────────────────────────────────────────────
export const link = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 12,
  padding: "13px 14px",
  borderRadius: 11,
  fontSize: 13,
  fontWeight: 800,
});

export const linkStyle = styleVariants({
  button: { border: `1px solid ${brand}`, background: brand, color: "#fff" },
  card: { border: `1px solid ${brand100}`, background: "#fff", color: brand },
});

// ── Files (`.cms-files`) ────────────────────────────────────────────────────────────────────
export const fileItem = style({
  display: "flex",
  alignItems: "center",
  gap: 11,
  padding: "12px 13px",
  border: `1px solid ${line}`,
  borderRadius: 11,
  background: "#fff",
  color: ink900,
});

export const fileIcon = style({
  display: "grid",
  flex: "none",
  width: 32,
  height: 32,
  placeItems: "center",
  overflow: "hidden",
  padding: 0,
  border: 0,
  borderRadius: 9,
  background: brand50,
  color: brand,
});

export const fileThumbButton = style([fileIcon, { cursor: "pointer" }]);

export const fileText = style({ display: "grid", gap: 2, minWidth: 0 });

export const fileTitle = style({ fontSize: 12.5, fontWeight: 700 });

export const fileDescription = style({ color: ink400, fontSize: 10.5 });

export const inlineImage = style({ width: "100%", borderRadius: 12, overflow: "hidden" });

// ── News (`.news-card`) ─────────────────────────────────────────────────────────────────────
export const newsCard = style({
  overflow: "hidden",
  border: `1px solid ${line}`,
  borderRadius: 16,
  background: "#fff",
});

export const newsBody = style({ padding: 12 });

export const newsTitle = style({ marginBottom: 4, fontSize: 14, fontWeight: 600, color: ink900 });

export const newsExcerpt = style({ marginBottom: 8, color: ink500, fontSize: 13, lineHeight: 1.4 });

export const newsFooter = style({ display: "flex", justifyContent: "space-between", gap: 8 });

export const newsCategory = style({
  padding: "1px 8px",
  borderRadius: 999,
  background: "rgba(0,0,0,0.05)",
  color: ink500,
  fontSize: 12,
});

export const newsDate = style({ color: ink400, fontSize: 12 });

export const muted = style({ color: ink300 });
