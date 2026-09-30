import { style } from "@vanilla-extract/css";

// `.card` is a plain global class with no width/overflow constraint of its own -- as a grid item
// in FormTestsPage's single-column `styles.main`, a very wide descendant (the 250+-column results
// table) can still inflate this card (and every ancestor up to the page) instead of being
// contained by the table's own `overflow: auto` wrapper, because a grid item's default
// `min-width: auto` resolves to its content's min-content size unless overflow on the item
// *itself* is non-visible. `overflow: hidden` + `min-width: 0` here forces this card to never be
// wider than its grid-allocated width, regardless of how wide anything inside it wants to be --
// the actual horizontal/vertical scrolling for that wide content still happens one level down, in
// `AttemptsWideTable`/`TestAttemptsTable`'s own `.tableWrap`.
export const card = style({
  minWidth: 0,
  overflow: "hidden",
});

export const toolbar = style({
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "var(--space-2)",
  flexWrap: "wrap",
  marginBottom: "var(--space-3)",
});

export const toolbarGroup = style({
  display: "flex",
  alignItems: "center",
  gap: "var(--space-2)",
  flexWrap: "wrap",
});
