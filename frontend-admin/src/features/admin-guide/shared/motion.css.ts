import { keyframes, style } from "@vanilla-extract/css";

/** Shared motion primitives for the guide; every animation is dropped under reduced motion. */
export const reducedMotion = "(prefers-reduced-motion: reduce)";

export const fadeUp = keyframes({
  from: { opacity: 0, transform: "translateY(12px)" },
  to: { opacity: 1, transform: "translateY(0)" },
});

export const flash = keyframes({
  "0%": { boxShadow: "0 0 0 0 rgba(62, 107, 170, 0.45)" },
  "100%": { boxShadow: "0 0 0 10px rgba(62, 107, 170, 0)" },
});

export const press = keyframes({
  "0%": { transform: "scale(1)" },
  "40%": { transform: "scale(0.94)" },
  "100%": { transform: "scale(1)" },
});

export const strike = keyframes({
  from: { backgroundSize: "0% 2px" },
  to: { backgroundSize: "100% 2px" },
});

/** Hidden until `revealShown` is added; used with `useInView`. */
export const reveal = style({
  opacity: 0,
  "@media": { [reducedMotion]: { opacity: 1 } },
});

export const revealShown = style({
  animation: `${fadeUp} 420ms ease-out both`,
  "@media": { [reducedMotion]: { animation: "none", opacity: 1 } },
});

export const flashOnce = style({
  animation: `${flash} 900ms ease-out`,
  "@media": { [reducedMotion]: { animation: "none" } },
});

export const pressOnce = style({
  animation: `${press} 420ms ease-out`,
  "@media": { [reducedMotion]: { animation: "none" } },
});

/** Static ring around the control the current step asks to press; flashes once when it appears. */
export const hotspot = style({
  // Doubled selector so the ring wins over the element's own class (e.g. a fade-in animation).
  selectors: {
    "&&": {
      outline: "2px solid var(--brand-500)",
      outlineOffset: 2,
      animation: `${flash} 900ms ease-out`,
    },
  },
  "@media": { [reducedMotion]: { selectors: { "&&": { animation: "none" } } } },
});

const changedFade = keyframes({
  from: { backgroundColor: "#ffe7a3" },
  to: { backgroundColor: "#fff4d6" },
});

/** Soft yellow fill for what changed on the current step — not clickable (unlike `hotspot`). */
export const changed = style({
  // Doubled selector so the fill wins over the element's own background.
  selectors: {
    "&&": {
      backgroundColor: "#fff4d6",
      boxShadow: "0 0 0 2px #f0d49a",
      animation: `${changedFade} 700ms ease-out`,
    },
  },
  "@media": { [reducedMotion]: { selectors: { "&&": { animation: "none" } } } },
});
